"""MILP model, solve, warm start and plan assembly (ARCHITECTURE.md section 9).

Objective and constraints C1-C6 as in section 9.2-9.4; coefficients come from feasibility arcs,
scenario tables, costmodel and config only. This module never reports net INR.
"""
from __future__ import annotations

import math
import time

import highspy
import pandas as pd
import pulp

from freshroute.config import (
    EPS_FEFO,
    FLOAT_TOL,
    HOURS_PER_DAY,
    LAMBDA_SPOIL,
    OVERSHIP_SLACK,
    PENALTY_MULT,
    PHI_BALANCE,
)
from freshroute.data.io import Scenario
from freshroute.domain import costmodel
from freshroute.domain.feasibility import build_arcs
from freshroute.domain.shelflife import decay
from freshroute.policies.base import PLAN_COLUMNS, TRIP_COLUMNS, Plan
from freshroute.solvers.greedy import classes, fefo_greedy, lookups

_IMPROVING = highspy.cb.HighsCallbackType.kCallbackMipImprovingSolution
_OK = (pulp.LpSolveStatus.Optimal, pulp.LpSolveStatus.TimeLimit, pulp.LpSolveStatus.GapLimit)


def model_data(sc: Scenario):
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


def solve(sc: Scenario, arcs, batches, unship, time_limit_s, gap, override=None,
           overship=OVERSHIP_SLACK, used=None, warm=None, fleet=None, on_incumbent=None):
    """Returns ((x, n) | None, info); None when there is no usable incumbent. `used` (replan,
    section 14.2): {"trips": {(v, day): n}, "recv": {(d, day): kg}} already taken by frozen
    shipments, subtracted from C3 and C4, plus "fill": {d: kg} counted in C6; `warm`: old plan
    rows offered as the warm start. n is keyed by (trip class, dest, day); C2 caps an arc
    vehicle's kg by the trips of all its classes (`fleet`, section 9.5; identity otherwise).
    `on_incumbent(x, n, profit)` is called with the starting plan and again for every better
    incumbent HiGHS finds (from its thread: copy and return fast), so a caller can show
    progress; profit is the model objective, never a reported KPI."""
    veh, lanes, dest, target = lookups(sc, override)
    f, cls = classes(veh, fleet)
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
    xd = {d: prob.add_variable(f"f_{d}", 0, None, cat="Continuous") for d in tot}  # kg to d
    for d in tot:  # one short row per destination keeps the average-fill row sparse
        prob += xd[d] == pulp.lpSum(x[i] for i in by_d[d]) + fill_used.get(d, 0.0)
    avg = prob.add_variable("avg_fill", 0, None, cat="Continuous")
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
        for d, var in xd.items():
            var.setInitialValue(gxd[d])
        for d, var in slack.items():
            var.setInitialValue(max(0.0, PHI_BALANCE * g_avg - gxd[d] / tot[d]))
        return warm is None or prob.valid(FLOAT_TOL)  # plain runs never pay for the check

    # Warm start from the FEFO-greedy plan: the incumbent is never worse than FEFO
    # under the MILP objective, even when the time limit stops the search early. A replan
    # (section 14.2) starts from the old plan's undispatched rows instead while they still
    # satisfy every constraint: fewest moves, and the old plan was itself optimized.
    if warm is None or not start(*warm_plan(arcs, warm, veh)):
        gx, gn = fefo_greedy(sc, arcs, batches, override, overship, used, fleet)
        start(gx, gn)
        if warm is None:  # FEFO ignores C6, so the rounded LP is usually the better start
            gobj = pulp.value(prob.objective)
            lp = _lp_start(prob)
            if lp is not None and lp[1] > gobj:
                for var, val in zip(prob.exported_variables(), lp[0], strict=True):
                    var.setInitialValue(val)
    cols = {v.name: j for j, v in enumerate(prob.exported_variables())}
    xi, nj = [cols[v.name] for v in x], {k: cols[v.name] for k, v in n.items()}

    def snapshot(vals):
        return ([max(0.0, vals[j]) for j in xi], {k: round(vals[j]) for k, j in nj.items()})

    hs = {}
    if on_incumbent:
        on_incumbent(*snapshot([v.varValue for v in prob.exported_variables()]),
                     pulp.value(prob.objective))

        def cb(cb_type, message, data_out, data_in, user_data):
            sol = data_out.mip_solution
            if sol is not None and len(sol) == len(cols):
                on_incumbent(*snapshot(sol), -data_out.objective_function_value)
        hs = {"callbackTuple": (cb, None), "callbacksToActivate": [_IMPROVING]}
    t0 = time.perf_counter()
    stats = prob.solve(pulp.HiGHS(msg=False, timeLimit=time_limit_s, gapRel=gap, warmStart=True,
                                  **hs))
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
        gx, gn = fefo_greedy(sc, arcs, batches, override, overship, used, fleet)
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


def _lp_start(prob):
    """Rounded-LP start (section 9.6): relax the trip integers, dive by rounding the most
    fractional third (or half) of them up and re-solving the LP (about 0.03 s each), keep the
    better dive. Returns (values in prob.exported_variables() order, profit) or None."""
    s = pulp.HiGHS(msg=False)
    s.createAndConfigureSolver(prob)
    s.buildSolverModel(prob)
    h = prob.solverModel
    cols = prob.exported_variables()
    integ = [j for j, v in enumerate(cols) if v.cat == pulp.LpInteger]
    for j in integ:
        h.changeColIntegrality(j, highspy.HighsVarType.kContinuous)
    best = None
    for share in (1 / 3, 1 / 2):
        for j in integ:
            h.changeColBounds(j, 0.0, highspy.kHighsInf)
        h.run()
        free = set(integ)
        while free and h.getModelStatus() == highspy.HighsModelStatus.kOptimal:
            sol = h.getSolution().col_value
            frac = {j: sol[j] - math.floor(sol[j] + FLOAT_TOL) for j in free}
            for j in [j for j in free if frac[j] < FLOAT_TOL]:
                free.discard(j)
                h.changeColBounds(j, round(sol[j]), round(sol[j]))
            if not free:
                break
            pick = sorted(free, key=lambda j: -frac[j])
            pick = pick[:max(1, int(len(pick) * share))]
            for j in pick:
                h.changeColBounds(j, math.ceil(sol[j] - FLOAT_TOL), math.ceil(sol[j] - FLOAT_TOL))
            h.run()
            if h.getModelStatus() != highspy.HighsModelStatus.kOptimal:  # C3 broke: round down
                for j in pick:
                    h.changeColBounds(j, math.floor(sol[j] + FLOAT_TOL),
                                      math.floor(sol[j] + FLOAT_TOL))
                h.run()
            free.difference_update(pick)
        if h.getModelStatus() == highspy.HighsModelStatus.kOptimal:
            obj = -h.getInfo().objective_function_value
            if best is None or obj > best[1]:
                vals = list(h.getSolution().col_value)
                for j in integ:
                    vals[j] = float(round(vals[j]))
                best = ([max(0.0, v) for v in vals], obj)
    return best


def warm_plan(arcs, warm: pd.DataFrame, veh):
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


def build_plan(sc: Scenario, arcs, x, n, solver: dict, policy: str) -> Plan:
    veh, lanes, _, _ = lookups(sc)
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
