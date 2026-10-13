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

import pandas as pd
import pulp

from freshroute import costmodel
from freshroute.config import (
    EPS_FEFO,
    FLOAT_TOL,
    LAMBDA_SPOIL,
    MILP_TIME_LIMIT_S,
    MIP_REL_GAP,
    OVERSHIP_SLACK,
    PENALTY_MULT,
    PHI_BALANCE,
)
from freshroute.feasibility import HOURS_PER_DAY, build_arcs
from freshroute.io import Scenario
from freshroute.policies.base import PLAN_COLUMNS, TRIP_COLUMNS, Plan, Policy
from freshroute.shelflife import decay

_OK = (pulp.LpSolveStatus.Optimal, pulp.LpSolveStatus.TimeLimit, pulp.LpSolveStatus.GapLimit)


def _model_data(sc: Scenario):
    """Feasible arcs with objective coefficient `coef`, batches, and unshipped penalty per kg."""
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
    arcs["coef"] = (arcs.margin_inr_kg
                    - LAMBDA_SPOIL * arcs.commodity.map(com.handling_loss_frac)
                    * arcs.commodity.map(s_c)
                    + EPS_FEFO / arcs.usable_life_at_arrival_h)
    arcs = arcs.sort_values(["batch_id", "dest_id", "vehicle_id", "dispatch_day"],
                            ignore_index=True)
    # e_b = 1 if unshipped stock would expire at origin within the horizon (section 13 step 3)
    dk = [decay(b.storage_temp_c[i], com.ref_temp_c[b.commodity[i]], com.q10[b.commodity[i]])
          for i in b.index]
    expires = (b.available_from_h + b.remaining_shelf_life_h / dk) <= horizon * HOURS_PER_DAY
    unship = {bid: LAMBDA_SPOIL * float(s_c[b.commodity[bid]]) * float(expires[bid])
              for bid in b.index}
    return arcs, b, unship


def _lookups(sc: Scenario, override: dict | None = None):
    t = sc.tables
    veh = t["vehicles"].set_index("vehicle_id")
    lanes = t["lanes"].set_index(["origin", "dest_id", "mode"])
    dest = t["destinations"].set_index("dest_id")
    target = t["demand"].set_index(["dest_id", "commodity", "day"]).demand_kg_p50.to_dict()
    target.update(override or {})  # demand_cap_override (section 14.3): {(d, c, day): kg}
    return veh, lanes, dest, target


def _solve(sc: Scenario, arcs, batches, unship, time_limit_s, gap, override=None):
    """Returns ((x, n) | None, info); None when there is no usable incumbent."""
    veh, lanes, dest, target = _lookups(sc, override)
    prob = pulp.LpProblem("freshroute_alloc", pulp.LpMaximize)
    x = [prob.add_variable(f"x{i}", 0, None, cat="Continuous") for i in range(len(arcs))]
    vdt = sorted({(a.vehicle_id, a.dest_id, a.dispatch_day) for a in arcs.itertuples()})
    n = {k: prob.add_variable(f"n_{k[0]}_{k[1]}_{k[2]}", 0, None, cat="Integer") for k in vdt}
    u = {bid: prob.add_variable(f"u_{bid}", 0, None, cat="Continuous") for bid in batches.index}
    fixed = {k: float(lanes.loc[(veh.origin[k[0]], k[1], veh["mode"][k[0]])].cost_fixed_inr_trip)
             for k in vdt}
    prob += (pulp.lpSum(float(c) * xi for c, xi in zip(arcs.coef, x, strict=True))
             - pulp.lpSum(fixed[k] * n[k] for k in vdt)
             - pulp.lpSum(unship[b] * u[b] for b in u))
    for bid, idx in arcs.groupby("batch_id").groups.items():  # C1 stock balance
        prob += pulp.lpSum(x[i] for i in idx) + u[bid] == float(batches.qty_kg[bid])
    for (v, d, day), idx in arcs.groupby(["vehicle_id", "dest_id", "dispatch_day"]).groups.items():
        prob += pulp.lpSum(x[i] for i in idx) <= float(veh.capacity_kg[v]) * n[(v, d, day)]  # C2
    for v, day in sorted({(k[0], k[2]) for k in vdt}):  # C3 trips per day
        prob += (pulp.lpSum(n[k] for k in vdt if k[0] == v and k[2] == day)
                 <= int(veh.max_trips_day[v]))
    for (d, _a), idx in arcs.groupby(["dest_id", "arrival_day"]).groups.items():  # C4 (D-05)
        prob += pulp.lpSum(x[i] for i in idx) <= float(dest.receive_cap_kg_day[d])
    tot: dict = {}  # T_d over reachable (d, c, a) keys
    for (d, c, a), idx in arcs.groupby(["dest_id", "commodity", "arrival_day"]).groups.items():
        tgt = float(target.get((d, c, a), 0.0))
        tot[d] = tot.get(d, 0.0) + tgt
        prob += pulp.lpSum(x[i] for i in idx) <= tgt * (1 + OVERSHIP_SLACK)  # C5 (D-05)
    tot = {d: v for d, v in sorted(tot.items()) if v > FLOAT_TOL}
    by_d = arcs.groupby("dest_id").groups
    xd = {d: pulp.lpSum(x[i] for i in by_d[d]) for d in tot}
    avg = prob.add_variable("avg_fill", 0, None, cat="Continuous")  # one row, keeps C6 sparse
    prob += avg == pulp.lpSum((1 / (len(tot) * tot[d])) * xd[d] for d in tot)
    slack = {d: prob.add_variable(f"s_{d}", 0, None, cat="Continuous") for d in tot}
    for d in tot:  # C6 soft fill balance, times T_d
        prob += xd[d] + tot[d] * slack[d] >= PHI_BALANCE * tot[d] * avg
    penalty = PENALTY_MULT * float(sc.tables["prices"].price_inr_kg.max())
    prob.setObjective(prob.objective - pulp.lpSum(penalty * tot[d] * slack[d] for d in tot))
    t0 = time.perf_counter()
    stats = prob.solve(pulp.HiGHS(msg=False, timeLimit=time_limit_s, gapRel=gap))
    info = {"status": str(stats.status), "solve_seconds": time.perf_counter() - t0}
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
    except Exception:  # noqa: BLE001  no incumbent
        return None, info
    if any(v is None or math.isnan(v) for v in xv):
        return None, info
    if stats.status == pulp.LpSolveStatus.TimeLimit and sum(xv) <= FLOAT_TOL:
        return None, info  # limit hit before any real incumbent: all-zero is not a plan
    return (xv, nv), info


def _greedy(sc: Scenario, arcs, batches, override: dict | None = None):
    """FEFO-greedy over feasible arcs honouring C2-C5 (earliest-expiry batch first)."""
    veh, _, dest, target = _lookups(sc, override)
    tgt = {k: v * (1 + OVERSHIP_SLACK) for k, v in target.items()}
    recv: dict = {}
    load: dict = {}  # (v,d,day) -> kg left on already-opened trips
    trips_day: dict = {}
    n: dict = {}
    x = [0.0] * len(arcs)
    expiry = batches.available_from_h + batches.remaining_shelf_life_h
    for bid in sorted(batches.index, key=lambda b: (expiry[b], b)):
        left = float(batches.qty_kg[bid])
        sub = arcs[arcs.batch_id == bid].sort_values(
            ["coef", "dest_id", "vehicle_id", "dispatch_day"], ascending=[False, True, True, True])
        for i, a in sub.iterrows():
            kd, ka = (a.dest_id, a.commodity, a.arrival_day), (a.dest_id, a.arrival_day)
            k, vd = (a.vehicle_id, a.dest_id, a.dispatch_day), (a.vehicle_id, a.dispatch_day)
            while left > FLOAT_TOL:
                room = min(tgt.get(kd, 0.0) - recv.get(kd, 0.0),
                           float(dest.receive_cap_kg_day[a.dest_id]) - recv.get(ka, 0.0))
                if room <= FLOAT_TOL:
                    break
                if load.get(k, 0.0) <= FLOAT_TOL:  # open a trip
                    if trips_day.get(vd, 0) >= int(veh.max_trips_day[a.vehicle_id]):
                        break
                    trips_day[vd] = trips_day.get(vd, 0) + 1
                    n[k] = n.get(k, 0) + 1
                    load[k] = load.get(k, 0.0) + float(veh.capacity_kg[a.vehicle_id])
                q = min(left, room, load[k])
                x[i] += q
                recv[kd] = recv.get(kd, 0.0) + q
                recv[ka] = recv.get(ka, 0.0) + q
                load[k] -= q
                left -= q
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


class MilpPolicy(Policy):
    name = "milp"

    def plan(self, scenario: Scenario, ctx: dict | None = None) -> Plan:
        ctx = ctx or {}
        arcs, batches, unship = _model_data(scenario)
        ov = ctx.get("demand_cap_override")
        sol, info = _solve(scenario, arcs, batches, unship,
                           ctx.get("time_limit_s", MILP_TIME_LIMIT_S), ctx.get("gap", MIP_REL_GAP),
                           override=ov)
        info["fallback_used"] = sol is None
        if sol is None:
            info.update(slack_usage={}, mip_gap=None)
        # AGENTS.md rule 6: never crash. ponytail: greedy ignores C6 and replan residuals.
        x, n = _greedy(scenario, arcs, batches, ov) if sol is None else sol
        return _build_plan(scenario, arcs, x, n, info, self.name)
