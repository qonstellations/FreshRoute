"""Allocation MILP, PuLP -> HiGHS (ARCHITECTURE.md section 9). Variables x, n, u, slack; C1-C6.

Objective per section 9.2: arc coef = margin_inr_kg (p(1-h) - c_var - hc_d, feasibility)
- lambda*h*s + eps/usable_life; minus fixed trip cost; minus lambda*s*e_b on unshipped kg.
Coefficients come from feasibility arcs, scenario tables, costmodel and config only. This
module never reports net INR. C6 (section 9.4) is soft: fill_d + slack_d >= PHI * avg_fill,
multiplied through by T_d, where T_d sums targets over (d, c, arrival_day) keys some feasible
arc reaches, so an unreachable destination cannot force slack.
"""
from __future__ import annotations

import math
import time
from dataclasses import replace

import pandas as pd
import pulp

from freshroute import costmodel
from freshroute.config import (
    AGG_ARC_THRESHOLD,
    AGG_RSL_BUCKET_H,
    EPS_FEFO,
    FLOAT_TOL,
    HOURS_PER_DAY,
    LAMBDA_SPOIL,
    MILP_TIME_LIMIT_S,
    MIP_REL_GAP,
    OVERSHIP_SLACK,
    PENALTY_MULT,
    PHI_BALANCE,
)
from freshroute.feasibility import build_arcs
from freshroute.io import Scenario
from freshroute.policies.base import PLAN_COLUMNS, TRIP_COLUMNS, Plan, Policy
from freshroute.shelflife import decay

_OK = (pulp.LpSolveStatus.Optimal, pulp.LpSolveStatus.TimeLimit, pulp.LpSolveStatus.GapLimit)


def _model_data(sc: Scenario):
    """Feasible arcs with objective coefficient `coef`, batches, and the per-kg INR spoilage cost
    of leaving each batch unshipped (s_c * e_b, before LAMBDA_SPOIL)."""
    t = sc.tables
    horizon = int(sc.meta["horizon_days"])
    arcs = build_arcs(sc)
    arcs = arcs[arcs.feasible & arcs.price_inr_kg.notna()].copy()
    b = t["batches"].sort_values("batch_id").set_index("batch_id")
    arcs["commodity"] = arcs.batch_id.map(b.commodity)
    com = t["commodities"].set_index("commodity")
    s_c = pd.Series({c: costmodel.spoilage_unit_cost(
        r.unit_cost_inr_kg, r.disposal_cost_inr_kg, r.salvage_value_inr_kg)
        for c, r in com.iterrows()})
    arcs["spoil_inr_kg"] = arcs.commodity.map(com.handling_loss_frac) * arcs.commodity.map(s_c)
    arcs["coef"] = (arcs.margin_inr_kg - LAMBDA_SPOIL * arcs.spoil_inr_kg
                    + EPS_FEFO / arcs.usable_life_at_arrival_h)
    arcs = arcs.sort_values(["batch_id", "dest_id", "vehicle_id", "dispatch_day"],
                            ignore_index=True)
    # e_b = 1 if unshipped stock would expire at origin within the horizon (section 13 step 3)
    dk = [decay(b.storage_temp_c[i], com.ref_temp_c[b.commodity[i]], com.q10[b.commodity[i]])
          for i in b.index]
    expires = (b.available_from_h + b.remaining_shelf_life_h / dk) <= horizon * HOURS_PER_DAY
    unship = {bid: float(s_c[b.commodity[bid]]) * float(expires[bid]) for bid in b.index}
    return arcs, b, unship


def _lookups(sc: Scenario, override: dict | None = None):
    t = sc.tables
    veh = t["vehicles"].set_index("vehicle_id")
    lanes = t["lanes"].set_index(["origin", "dest_id", "mode"])
    dest = t["destinations"].set_index("dest_id")
    target = t["demand"].set_index(["dest_id", "commodity", "day"]).demand_kg_p50.to_dict()
    target.update(override or {})  # demand_cap_override (section 14.3): {(d, c, day): kg}
    return veh, lanes, dest, target


def _classes(veh: pd.DataFrame, fleet: pd.DataFrame | None):
    """Trip classes per arc vehicle: (class table, {arc vehicle_id: [class ids]}). Identity
    (every vehicle its own class) unless the section 9.5 fallback pools the fleet."""
    f = veh.assign(lane_class=veh.index) if fleet is None else fleet
    return f, {v: list(g.index) for v, g in f.groupby("lane_class", sort=True)}


def _solve(sc: Scenario, arcs, batches, unship, time_limit_s, gap, override=None,
           overship=OVERSHIP_SLACK, used=None, warm=None, fleet=None):
    """Returns ((x, n) | None, info); None when there is no usable incumbent. `used` (replan,
    section 14.2): {"trips": {(v, day): n}, "recv": {(d, day): kg}} already taken by frozen
    shipments, subtracted from C3 and C4, plus "fill": {d: kg} counted in C6; `warm`: old plan
    rows offered as the warm start. n is keyed by (trip class, dest, day); C2 caps an arc
    vehicle's kg by the trips of all its classes (`fleet`, section 9.5; identity otherwise)."""
    veh, lanes, dest, target = _lookups(sc, override)
    f, cls = _classes(veh, fleet)
    trips_used, recv_used = (used or {}).get("trips", {}), (used or {}).get("recv", {})
    fill_used = (used or {}).get("fill", {})  # frozen kg per dest, counted in C6 fill
    prob = pulp.LpProblem("freshroute_alloc", pulp.LpMaximize)
    x = [prob.add_variable(f"x{i}", 0, None, cat="Continuous") for i in range(len(arcs))]
    vdt = sorted({(a.vehicle_id, a.dest_id, a.dispatch_day) for a in arcs.itertuples()})
    nk = sorted({(c, d, day) for v, d, day in vdt for c in cls[v]})
    n = {k: prob.add_variable(f"n_{k[0]}_{k[1]}_{k[2]}", 0, None, cat="Integer") for k in nk}
    u = {bid: prob.add_variable(f"u_{bid}", 0, None, cat="Continuous") for bid in batches.index}
    fixed = {k: float(lanes.loc[(f.origin[k[0]], k[1], f["mode"][k[0]])].cost_fixed_inr_trip)
             for k in nk}
    prob += (pulp.lpSum(float(c) * xi for c, xi in zip(arcs.coef, x, strict=True))
             - pulp.lpSum(fixed[k] * n[k] for k in nk)
             - pulp.lpSum(LAMBDA_SPOIL * unship[b] * u[b] for b in u))
    by_b = arcs.groupby("batch_id").groups
    for bid in batches.index:  # C1 stock balance; arc-less batches too, so u = qty
        prob += pulp.lpSum(x[i] for i in by_b.get(bid, [])) + u[bid] == float(batches.qty_kg[bid])
    for (v, d, day), idx in arcs.groupby(["vehicle_id", "dest_id", "dispatch_day"]).groups.items():
        prob += pulp.lpSum(x[i] for i in idx) <= pulp.lpSum(  # C2
            float(f.capacity_kg[c]) * n[(c, d, day)] for c in cls[v])
    for c, day in sorted({(k[0], k[2]) for k in nk}):  # C3 trips per day
        prob += (pulp.lpSum(n[k] for k in nk if k[0] == c and k[2] == day)
                 <= max(0, int(f.max_trips_day[c]) - trips_used.get((c, day), 0)))
    for (d, _a), idx in arcs.groupby(["dest_id", "arrival_day"]).groups.items():  # C4 (D-05)
        prob += (pulp.lpSum(x[i] for i in idx)
                 <= max(0.0, float(dest.receive_cap_kg_day[d]) - recv_used.get((d, _a), 0.0)))
    tot: dict = {}  # T_d over reachable (d, c, a) keys
    for (d, c, a), idx in arcs.groupby(["dest_id", "commodity", "arrival_day"]).groups.items():
        tgt = float(target.get((d, c, a), 0.0))
        tot[d] = tot.get(d, 0.0) + tgt
        prob += pulp.lpSum(x[i] for i in idx) <= tgt * (1 + overship)  # C5 (D-05)
    tot = {d: v + fill_used.get(d, 0.0) for d, v in sorted(tot.items())}
    tot = {d: v for d, v in tot.items() if v > FLOAT_TOL}
    by_d = arcs.groupby("dest_id").groups
    xd = {d: pulp.lpSum(x[i] for i in by_d[d]) for d in tot}
    for d in sorted(set(fill_used) & set(xd)):
        xd[d] += fill_used[d]
    avg = prob.add_variable("avg_fill", 0, None, cat="Continuous")  # one row, keeps C6 sparse
    prob += avg == pulp.lpSum((1 / (len(tot) * tot[d])) * xd[d] for d in tot)
    slack = {d: prob.add_variable(f"s_{d}", 0, None, cat="Continuous") for d in tot}
    for d in tot:  # C6 soft fill balance, times T_d
        prob += xd[d] + tot[d] * slack[d] >= PHI_BALANCE * tot[d] * avg
    penalty = PENALTY_MULT * float(sc.tables["prices"].price_inr_kg.max())
    prob.setObjective(prob.objective - pulp.lpSum(penalty * tot[d] * slack[d] for d in tot))

    def start(gx, gn) -> bool:
        """Set the warm start; False if it breaks a constraint."""
        for var, val in zip(x, gx, strict=True):
            var.setInitialValue(val)
        for k, var in n.items():
            var.setInitialValue(gn.get(k, 0))
        for bid, var in u.items():
            var.setInitialValue(max(0.0, float(batches.qty_kg[bid])
                                    - sum(gx[i] for i in by_b.get(bid, []))))
        gxd = {d: sum(gx[i] for i in by_d[d]) + fill_used.get(d, 0.0) for d in tot}
        g_avg = sum(gxd[d] / (len(tot) * tot[d]) for d in tot)
        avg.setInitialValue(g_avg)
        for d, var in slack.items():
            var.setInitialValue(max(0.0, PHI_BALANCE * g_avg - gxd[d] / tot[d]))
        return warm is None or prob.valid(FLOAT_TOL)  # plain runs never pay for the check

    # Warm start from the FEFO-greedy plan: the incumbent is never worse than FEFO
    # under the MILP objective, even when the time limit stops the search early. A replan
    # (section 14.2) starts from the old plan's undispatched rows instead while they still
    # satisfy every constraint: fewest moves, and the old plan was itself optimized.
    if warm is None or not start(*_warm(arcs, warm, veh)):
        start(*_greedy(sc, arcs, batches, override, overship, used, fleet))
    t0 = time.perf_counter()
    stats = prob.solve(pulp.HiGHS(msg=False, timeLimit=time_limit_s, gapRel=gap, warmStart=True))
    info = {"status": str(stats.status), "solve_seconds": time.perf_counter() - t0,
            "size": {"vars": prob.numVariables(), "constraints": prob.numConstraints()}}
    try:  # HiGHS's own gap; pulp's stats.gap_rel is None for HiGHS
        g = float(prob.solverModel.getInfo().mip_gap)
    except Exception:  # noqa: BLE001
        g = 0.0 if stats.status == pulp.LpSolveStatus.Optimal else math.nan
    info["mip_gap"] = g if math.isfinite(g) else None
    if stats.status not in _OK:
        return None, info
    try:
        xv = [v.value() for v in x]
        nv = {k: v.value() for k, v in n.items()}
        info["slack_usage"] = {d: float(v.value()) for d, v in slack.items()
                               if (v.value() or 0.0) > FLOAT_TOL}
        # plain-INR objective (lambda = 1, no FEFO tie-break, no C6 slack penalty)
        econ = arcs.margin_inr_kg - arcs.spoil_inr_kg
        info["objective_inr"] = float(
            sum(float(c) * xi for c, xi in zip(econ, xv, strict=True))
            - sum(fixed[k] * nv[k] for k in nk) - sum(unship[b] * u[b].value() for b in u))
    except Exception:  # noqa: BLE001  no incumbent
        return None, info
    if any(v is None or math.isnan(v) for v in xv):
        return None, info
    if stats.status == pulp.LpSolveStatus.TimeLimit and sum(xv) <= FLOAT_TOL:
        return None, info  # limit hit before any real incumbent: all-zero is not a plan
    if stats.status != pulp.LpSolveStatus.Optimal:
        # A time-limited incumbent can be worse than the FEFO-greedy plan (HiGHS may drop the
        # warm start for a trivial point): keep whichever earns more at lambda = 1.
        gx, gn = _greedy(sc, arcs, batches, override, overship, used, fleet)
        by = pd.Series(gx).groupby(arcs.batch_id.values).sum()
        g_obj = float(
            sum(float(c) * xi for c, xi in zip(econ, gx, strict=True))
            - sum(fixed[k] * q for k, q in gn.items())
            - sum(unship[b] * max(0.0, float(batches.qty_kg[b]) - float(by.get(b, 0.0)))
                  for b in u))
        if g_obj > info["objective_inr"] + FLOAT_TOL:
            info.update(objective_inr=g_obj, incumbent="greedy")
            return (gx, gn), info
    return (xv, nv), info


def _greedy(sc: Scenario, arcs, batches, override: dict | None = None,
            overship: float = OVERSHIP_SLACK, used: dict | None = None,
            fleet: pd.DataFrame | None = None):
    """FEFO-greedy over feasible arcs honouring C2-C5 (earliest-expiry batch first)."""
    veh, _, dest, target = _lookups(sc, override)
    f, cls = _classes(veh, fleet)
    tgt = {k: v * (1 + overship) for k, v in target.items()}
    recv: dict = dict((used or {}).get("recv", {}))  # (d, day) keys only; frozen arrivals
    load: dict = {}  # (v,d,day) -> kg left on already-opened trips
    trips_day: dict = dict((used or {}).get("trips", {}))
    n: dict = {}
    x = [0.0] * len(arcs)
    expiry = batches.available_from_h + batches.remaining_shelf_life_h
    for bid in sorted(batches.index, key=lambda b: (expiry[b], b)):
        left = float(batches.qty_kg[bid])
        sub = arcs[arcs.batch_id == bid].sort_values(
            ["coef", "dest_id", "vehicle_id", "dispatch_day"], ascending=[False, True, True, True])
        for i, a in sub.iterrows():
            kd, ka = (a.dest_id, a.commodity, a.arrival_day), (a.dest_id, a.arrival_day)
            k = (a.vehicle_id, a.dest_id, a.dispatch_day)
            while left > FLOAT_TOL:
                room = min(tgt.get(kd, 0.0) - recv.get(kd, 0.0),
                           float(dest.receive_cap_kg_day[a.dest_id]) - recv.get(ka, 0.0))
                if room <= FLOAT_TOL:
                    break
                if load.get(k, 0.0) <= FLOAT_TOL:  # open a trip on the first class with a slot
                    c = next((c for c in cls[a.vehicle_id] if trips_day.get((c, a.dispatch_day), 0)
                              < int(f.max_trips_day[c])), None)
                    if c is None:
                        break
                    trips_day[(c, a.dispatch_day)] = trips_day.get((c, a.dispatch_day), 0) + 1
                    n[(c, *k[1:])] = n.get((c, *k[1:]), 0) + 1
                    load[k] = load.get(k, 0.0) + float(f.capacity_kg[c])
                q = min(left, room, load[k])
                x[i] += q
                recv[kd] = recv.get(kd, 0.0) + q
                recv[ka] = recv.get(ka, 0.0) + q
                load[k] -= q
                left -= q
    return x, n


def _warm(arcs, warm: pd.DataFrame, veh):
    """Plan rows (batch, dest, vehicle, dispatch_day, kg) as (x, n); rows whose arc is no
    longer feasible are dropped (their kg goes back to u)."""
    keys = ["batch_id", "dest_id", "vehicle_id", "dispatch_day"]
    kg = warm.groupby(keys).kg.sum()
    x = [float(kg.get(k, 0.0)) for k in arcs[keys].itertuples(index=False, name=None)]
    load: dict = {}
    for k, q in zip(arcs[keys[1:]].itertuples(index=False, name=None), x, strict=True):
        load[k] = load.get(k, 0.0) + q
    cap = veh.capacity_kg.astype(float)  # a 0-capacity vehicle leaves n = 0: C2 fails, invalid
    n = {(v, d, day): math.ceil(q / cap[v] - FLOAT_TOL) if cap[v] > 0 else 0
         for (d, v, day), q in load.items() if q > FLOAT_TOL}
    return x, n


def _build_plan(sc: Scenario, arcs, x, n, solver: dict, policy: str) -> Plan:
    veh, lanes, _, _ = _lookups(sc)
    a = arcs.assign(kg=x)
    a = a[a.kg > FLOAT_TOL].copy()
    a["priority_score"] = a.kg * a.price_inr_kg / a.usable_life_at_arrival_h
    a = a.sort_values(["priority_score", "batch_id", "dest_id"],
                      ascending=[False, True, True], ignore_index=True)
    a["priority_rank"] = range(1, len(a) + 1)
    ship, trips = [], []
    for (v, d, day), g in a.groupby(["vehicle_id", "dest_id", "dispatch_day"], sort=True):
        cap = float(veh.capacity_kg[v])
        ln = lanes.loc[(veh.origin[v], d, veh["mode"][v])]
        k_trips = max(int(round(n.get((v, d, day), 0))), math.ceil(g.kg.sum() / cap - FLOAT_TOL))
        used = [0.0] * k_trips
        disp = float(g.dispatch_h.max())
        for r in g.sort_values("priority_rank").to_dict("records"):  # first-fit, lines may split
            left = r["kg"]
            for k in range(k_trips):
                q = min(left, cap - used[k])
                if q <= FLOAT_TOL:
                    continue
                used[k] += q
                left -= q
                ship.append({**r, "kg": q, "trip_id": f"T-{v}-{d}-{day}-{k + 1}"})
                if left <= FLOAT_TOL:
                    break
        for k, kg in enumerate(used):
            if kg > FLOAT_TOL:
                trips.append({
                    "trip_id": f"T-{v}-{d}-{day}-{k + 1}", "vehicle_id": v,
                    "origin": veh.origin[v], "dest_id": d, "mode": veh["mode"][v],
                    "dispatch_day": day, "dispatch_h": disp, "kg_total": kg, "capacity_kg": cap,
                    "utilization_pct": 100 * kg / cap,
                    "cost_fixed_inr": float(ln.cost_fixed_inr_trip),
                    "cost_var_inr": kg * float(ln.cost_var_inr_kg)})
    p = pd.DataFrame(ship, columns=[*a.columns, "trip_id"])
    p = p.sort_values("priority_rank", kind="stable", ignore_index=True)
    p["shipment_id"] = [f"S{i + 1:04d}" for i in range(len(p))]
    p["is_frozen"] = False
    p["policy"] = policy
    return Plan(p.reindex(columns=list(PLAN_COLUMNS)),
                pd.DataFrame(trips, columns=list(TRIP_COLUMNS)), solver)


def _aggregate(sc: Scenario) -> tuple[Scenario, dict[str, pd.DataFrame]]:
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


def _split_fleet(lines: pd.DataFrame, n: dict, fleet: pd.DataFrame, vmem: dict,
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


def _plan_aggregated(sc: Scenario, ctx: dict, policy: str) -> Plan:
    """Aggregate -> solve -> split each pseudo-batch arc pro rata to qty_kg -> keep only lines
    whose batch-level arc is feasible -> independent validator; any violation left -> FEFO-greedy
    on the full scenario (section 9.5)."""
    from validator.validate import validate  # independent re-check (D-04); validator never
    # imports this module, so the dependency stays one-way.

    agg, members, fleet, vmem = _aggregate(sc)
    arcs, batches, unship = _model_data(agg)
    ov, slack = ctx.get("demand_cap_override"), ctx.get("overship_slack", OVERSHIP_SLACK)
    used = ctx.get("residual_use")
    frozen = (used or {}).get("trips", {})  # replan: concrete (v, day) trips -> class keys
    cls_of = {vid: c for c, g in vmem.items() for vid in g.vehicle_id}
    tc: dict = {}
    for (vid, day), k in sorted(frozen.items()):
        if vid in cls_of:
            tc[(cls_of[vid], day)] = tc.get((cls_of[vid], day), 0) + k
    used_c = {**used, "trips": tc} if used else None
    sol, info = _solve(agg, arcs, batches, unship, ctx.get("time_limit_s", MILP_TIME_LIMIT_S),
                       ctx.get("gap", MIP_REL_GAP), override=ov, overship=slack,
                       used=used_c, fleet=fleet)
    info["fallback_used"] = sol is None
    if sol is None:
        info.update(slack_usage={}, mip_gap=None)
    x, n = _greedy(agg, arcs, batches, ov, slack, used_c, fleet) if sol is None else sol
    keys = ["batch_id", "dest_id", "vehicle_id", "dispatch_day"]
    lines = []
    for a, kg in zip(arcs[keys].itertuples(index=False), x, strict=True):
        if kg > FLOAT_TOL:
            g = members[a.batch_id]
            lines += [(bid, a.dest_id, a.vehicle_id, a.dispatch_day, kg * q / g.qty_kg.sum())
                      for bid, q in zip(g.batch_id, g.qty_kg, strict=True)]
    lines = pd.DataFrame(lines, columns=[*keys, "kg"])
    # Batch-level feasibility re-check, only for the batches and dests in use; members of a
    # lane class share every arc attribute, so the lane-class row stands in for them.
    t, va = sc.tables, agg.tables["vehicles"]
    sub = replace(sc, tables={
        **t, "batches": t["batches"][t["batches"].batch_id.isin(lines.batch_id)],
        "destinations": t["destinations"][t["destinations"].dest_id.isin(lines.dest_id)],
        "vehicles": va[va.vehicle_id.isin(lines.vehicle_id)]})
    full, _, _ = _model_data(sub) if len(lines) else (arcs.iloc[:0], None, None)
    full = full.merge(lines, on=keys, how="inner")  # infeasible batch-level arcs drop out
    n_drop = len(lines) - len(full)
    split, n = _split_fleet(full, n, fleet, vmem, frozen)
    plan = _build_plan(sc, split.drop(columns="kg"), list(split.kg), n, info, policy)
    viol = validate(sc, plan.plan).violation_total
    info["aggregation"] = {"batches": len(t["batches"]), "groups": len(members),
                           "vehicle_classes": len(fleet), "agg_arcs": len(arcs),
                           "dropped_lines": n_drop,
                           "unassigned_kg": float(full.kg.sum() - split.kg.sum()),
                           "validator_violations": viol}
    if viol:  # AGENTS.md rule 6: never ship a violating plan
        arcs, batches, _ = _model_data(sc)
        info.update(fallback_used=True, slack_usage={}, mip_gap=None)
        x, n = _greedy(sc, arcs, batches, ov, slack, used)
        plan = _build_plan(sc, arcs, x, n, info, policy)
    return plan


def _candidate_arcs(sc: Scenario) -> int:
    """Rows build_arcs would produce: batches x dests x vehicles x days (cheap size check)."""
    t = sc.tables
    return (len(t["batches"]) * len(t["destinations"]) * len(t["vehicles"])
            * int(sc.meta["horizon_days"]))


class MilpPolicy(Policy):
    name = "milp"

    def plan(self, scenario: Scenario, ctx: dict | None = None) -> Plan:
        ctx = ctx or {}
        if _candidate_arcs(scenario) > ctx.get("agg_threshold", AGG_ARC_THRESHOLD):
            return _plan_aggregated(scenario, ctx, self.name)
        arcs, batches, unship = _model_data(scenario)
        ov = ctx.get("demand_cap_override")
        slack = ctx.get("overship_slack", OVERSHIP_SLACK)  # sensitivity
        used = ctx.get("residual_use")  # replan: frozen trips and arrivals
        sol, info = _solve(scenario, arcs, batches, unship,
                           ctx.get("time_limit_s", MILP_TIME_LIMIT_S), ctx.get("gap", MIP_REL_GAP),
                           override=ov, overship=slack, used=used,
                           warm=ctx.get("warm_start"))
        info["fallback_used"] = sol is None
        if sol is None:
            info.update(slack_usage={}, mip_gap=None)
        # AGENTS.md rule 6: never crash. ponytail: greedy ignores C6 and replan residuals.
        x, n = _greedy(scenario, arcs, batches, ov, slack, used) if sol is None else sol
        return _build_plan(scenario, arcs, x, n, info, self.name)


class MilpMarkdownPolicy(MilpPolicy):
    """milp_markdown (ARCHITECTURE.md sections 10, 12): MILP plan + tiered markdown."""

    name = "milp_markdown"

    def plan(self, scenario: Scenario, ctx: dict | None = None) -> Plan:
        from freshroute.discount import build_discounts

        p = super().plan(scenario, ctx)
        p.plan["policy"] = self.name
        p.discounts = build_discounts(scenario, p.plan)
        return p
