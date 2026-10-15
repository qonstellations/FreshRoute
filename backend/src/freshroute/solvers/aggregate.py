"""Scale fallback: aggregate batches and fleet, solve, disaggregate (ARCHITECTURE.md 9.5)."""
from __future__ import annotations

from dataclasses import replace

import pandas as pd

from freshroute.config import AGG_RSL_BUCKET_H, FLOAT_TOL
from freshroute.data.io import Scenario
from freshroute.policies.base import Plan
from freshroute.solvers import milp_model
from freshroute.solvers.greedy import fefo_greedy


def aggregate(sc: Scenario) -> tuple[Scenario, dict[str, pd.DataFrame]]:
    """Section 9.5 scale fallback: one pseudo-batch per (commodity, origin, available_from_h,
    RSL bucket). The representative takes the group's min RSL and max storage temp, so every
    arc feasible for it is feasible for each member (wait >= 0, same dispatch hour)."""
    b = sc.tables["batches"].sort_values("batch_id")
    key = [b.commodity, b.origin_hub, b.available_from_h,
           (b.remaining_shelf_life_h // AGG_RSL_BUCKET_H).rename("bucket")]
    rows, members = [], {}
    for i, (_, g) in enumerate(b.groupby(key, sort=True)):
        gid = f"G{i + 1:05d}"
        members[gid] = g
        rows.append({**g.iloc[0].to_dict(), "batch_id": gid, "qty_kg": float(g.qty_kg.sum()),
                     "remaining_shelf_life_h": float(g.remaining_shelf_life_h.min()),
                     "rsl_p10_h": float(g.rsl_p10_h.min()), "rsl_p90_h": float(g.rsl_p90_h.min()),
                     "storage_temp_c": float(g.storage_temp_c.max())})
    # Fleet (A-46): vehicles sharing (origin, mode, available_from_h) have identical arcs, so
    # one lane-class row carries the arcs; its trips come from capacity classes (C2/C3 only).
    v = sc.tables["vehicles"]
    v = v[v.max_trips_day > 0].sort_values("vehicle_id")
    lanes, classes, vmem = [], [], {}
    for i, (_, g) in enumerate(v.groupby(["origin", "mode", "available_from_h"], sort=True)):
        lid = f"L{i + 1:03d}"
        lanes.append({**g.iloc[0].to_dict(), "vehicle_id": lid,
                      "capacity_kg": float(g.capacity_kg.max()),
                      "max_trips_day": int(g.max_trips_day.sum())})
        for cap, cg in sorted(g.groupby("capacity_kg"), key=lambda kv: -kv[0]):  # big first
            cid = f"{lid}K{len(classes) + 1:03d}"
            vmem[cid] = cg
            classes.append({"class_id": cid, "origin": cg.origin.iloc[0],
                            "mode": cg["mode"].iloc[0], "capacity_kg": float(cap),
                            "max_trips_day": int(cg.max_trips_day.sum()), "lane_class": lid})
    fleet = pd.DataFrame(classes, columns=["class_id", "origin", "mode", "capacity_kg",
                                           "max_trips_day", "lane_class"]).set_index("class_id")
    agg = replace(sc, tables={**sc.tables, "batches": pd.DataFrame(rows, columns=b.columns),
                              "vehicles": pd.DataFrame(lanes, columns=v.columns)})
    return agg, members, fleet, vmem


def split_fleet(lines: pd.DataFrame, n: dict, fleet: pd.DataFrame, vmem: dict,
                 frozen: dict | None = None):
    """Hand each class's trips to member vehicles within their max_trips_day (less `frozen`
    replan trips), then fill each (lane class, dest, day)'s lines first-fit into those
    vehicles' kg. Returns (lines, n)."""
    used: dict = dict(frozen or {})
    bins: dict = {}  # (lane class, dest, day) -> [[vehicle_id, room_kg]]
    nv: dict = {}
    for (c, d, day), k in sorted(n.items()):
        k = int(round(k or 0))
        for vid, mx in zip(vmem[c].vehicle_id, vmem[c].max_trips_day, strict=True):
            t = min(k, int(mx) - used.get((vid, day), 0))
            if t > 0:
                used[(vid, day)] = used.get((vid, day), 0) + t
                nv[(vid, d, day)] = t
                bins.setdefault((fleet.lane_class[c], d, day), []).append(
                    [vid, t * float(fleet.capacity_kg[c])])
                k -= t
    out = []
    for key, g in lines.groupby(["vehicle_id", "dest_id", "dispatch_day"], sort=True):
        bs = bins.get(key, [])
        for r in g.to_dict("records"):
            left = r["kg"]
            for j, b in enumerate(bs):  # ponytail: FLOAT_TOL residue rides the last bin
                q = left if j == len(bs) - 1 else min(left, b[1])
                if q > FLOAT_TOL:
                    out.append({**r, "vehicle_id": b[0], "kg": q})
                    b[1] -= q
                    left -= q
    return pd.DataFrame(out, columns=lines.columns), nv


def plan_aggregated(sc: Scenario, ctx: dict, policy: str, time_limit_s: float, gap: float,
                    overship: float) -> Plan:
    """Aggregate -> solve -> split each pseudo-batch arc pro rata to qty_kg -> keep only lines
    whose batch-level arc is feasible -> independent validator; any violation left -> FEFO-greedy
    on the full scenario (section 9.5)."""
    from validator.validate import validate  # independent re-check (D-04); validator never
    # imports this module, so the dependency stays one-way.

    agg, members, fleet, vmem = aggregate(sc)
    arcs, batches, unship = milp_model.model_data(agg)
    ov, slack = ctx.get("demand_cap_override"), overship
    used = ctx.get("residual_use")
    frozen = (used or {}).get("trips", {})  # replan: concrete (v, day) trips -> class keys
    cls_of = {vid: c for c, g in vmem.items() for vid in g.vehicle_id}
    tc: dict = {}
    for (vid, day), k in sorted(frozen.items()):
        if vid in cls_of:
            tc[(cls_of[vid], day)] = tc.get((cls_of[vid], day), 0) + k
    used_c = {**used, "trips": tc} if used else None
    keys = ["batch_id", "dest_id", "vehicle_id", "dispatch_day"]
    t, va = sc.tables, agg.tables["vehicles"]

    def assemble(x, n, info):
        """Pseudo-batch (x, n) -> concrete Plan and its validator violation count."""
        lines = []
        for a, kg in zip(arcs[keys].itertuples(index=False), x, strict=True):
            if kg > FLOAT_TOL:
                g = members[a.batch_id]
                lines += [(bid, a.dest_id, a.vehicle_id, a.dispatch_day, kg * q / g.qty_kg.sum())
                          for bid, q in zip(g.batch_id, g.qty_kg, strict=True)]
        lines = pd.DataFrame(lines, columns=[*keys, "kg"])
        # Batch-level feasibility re-check, only for the batches and dests in use; members of a
        # lane class share every arc attribute, so the lane-class row stands in for them.
        sub = replace(sc, tables={
            **t, "batches": t["batches"][t["batches"].batch_id.isin(lines.batch_id)],
            "destinations": t["destinations"][t["destinations"].dest_id.isin(lines.dest_id)],
            "vehicles": va[va.vehicle_id.isin(lines.vehicle_id)]})
        full, _, _ = milp_model.model_data(sub) if len(lines) else (arcs.iloc[:0], None, None)
        full = full.merge(lines, on=keys, how="inner")  # infeasible batch-level arcs drop out
        n_drop = len(lines) - len(full)
        split, n = split_fleet(full, n, fleet, vmem, frozen)
        plan = milp_model.build_plan(sc, split.drop(columns="kg"), list(split.kg), n, info,
                                     policy)
        viol = validate(sc, plan.plan).violation_total
        info["aggregation"] = {"batches": len(t["batches"]), "groups": len(members),
                               "vehicle_classes": len(fleet), "agg_arcs": len(arcs),
                               "dropped_lines": n_drop,
                               "unassigned_kg": float(full.kg.sum() - split.kg.sum()),
                               "validator_violations": viol}
        return plan, viol

    on_plan, inc = ctx.get("on_plan"), None
    if on_plan:  # progressive run: offer every incumbent as a plan (None when it violates)
        def inc(x, n, profit):
            def make():
                plan, viol = assemble(x, n, {"status": "incumbent"})
                return None if viol else plan
            on_plan(make, profit)
    sol, info = milp_model.solve(agg, arcs, batches, unship, time_limit_s, gap,
                                 override=ov, overship=slack, used=used_c, fleet=fleet,
                                 on_incumbent=inc)
    info["fallback_used"] = sol is None
    if sol is None:
        info.update(slack_usage={}, mip_gap=None)
    x, n = fefo_greedy(agg, arcs, batches, ov, slack, used_c, fleet) if sol is None else sol
    plan, viol = assemble(x, n, info)
    if viol:  # AGENTS.md rule 6: never ship a violating plan
        arcs, batches, _ = milp_model.model_data(sc)
        info.update(fallback_used=True, slack_usage={}, mip_gap=None)
        x, n = fefo_greedy(sc, arcs, batches, ov, slack, used)
        plan = milp_model.build_plan(sc, arcs, x, n, info, policy)
    return plan
