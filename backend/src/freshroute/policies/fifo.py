"""FIFO-nearest baseline (ARCHITECTURE.md section 12, A-31): oldest batch first, to the nearest
destination with remaining demand. Respects vehicle capacity, trips/day, receiving capacity
and the p50 demand cap but not shelf life or delivery windows (naive dispatcher); the
validator reports what that costs. Never computes net INR (AGENTS.md rule 3).
"""
from __future__ import annotations

from collections import defaultdict

import pandas as pd

from freshroute.config import FLOAT_TOL
from freshroute.data.io import Scenario
from freshroute.domain.feasibility import build_arcs
from freshroute.policies.base import PLAN_COLUMNS, TRIP_COLUMNS, Plan, Policy

# Naive FIFO per ARCH 12 (A-31): window/shelf-life rejects are usable, violations are reported
# honestly. Physical rejects (NO_LANE, NOT_AVAILABLE, RAIL_SLOT) stay out; the
# arrival_day < horizon filter below still drops BEYOND_HORIZON arcs (no demand/price there).
_USABLE = ("", "WINDOW", "SHELF_LIFE", "BEYOND_HORIZON")


class FifoPolicy(Policy):
    name = "fifo"

    def plan(self, scenario: Scenario, ctx: dict | None = None) -> Plan:
        t = scenario.tables
        horizon = int(scenario.meta["horizon_days"])
        arcs = build_arcs(scenario)
        arcs = arcs[arcs.reject_reason.fillna("").isin(_USABLE) & (arcs.arrival_day < horizon)]
        arcs = arcs.assign(tr=arcs.arrival_h - arcs.dispatch_h)
        batches = t["batches"].sort_values(["available_from_h", "batch_id"])
        veh = t["vehicles"].set_index("vehicle_id")
        lanes = t["lanes"].set_index(["origin", "dest_id", "mode"])
        price = t["prices"].set_index(["dest_id", "commodity", "day"]).price_inr_kg
        left_dem = t["demand"].set_index(["dest_id", "commodity", "day"]).demand_kg_p50.to_dict()
        recv_cap = t["destinations"].set_index("dest_id").receive_cap_kg_day.to_dict()
        recv: dict = defaultdict(float)
        trips: dict[str, dict] = {}
        trips_used: dict = defaultdict(int)  # (vehicle, day) -> trips opened
        lines: list[dict] = []
        stock = batches.set_index("batch_id").qty_kg.to_dict()

        for b in batches.itertuples():
            ba = arcs[arcs.batch_id == b.batch_id]
            for day in range(horizon):
                da = ba[ba.dispatch_day == day]
                # nearest destination first, then earliest arrival, then ids (deterministic)
                da = da.sort_values(["tr", "dest_id", "arrival_h", "vehicle_id"], kind="stable")
                for a in da.itertuples():
                    if stock[b.batch_id] <= FLOAT_TOL:
                        break
                    dkey = (a.dest_id, b.commodity, int(a.arrival_day))
                    rkey = (a.dest_id, int(a.arrival_day))
                    cap = float(veh.loc[a.vehicle_id, "capacity_kg"])
                    same = [k for k, v in trips.items() if (
                        v["vehicle"], v["dest"], v["day"]) == (a.vehicle_id, a.dest_id, day)]
                    # reuse an open trip with the same departure, else open a new one if allowed
                    tid = next((k for k in same
                                if abs(trips[k]["dispatch_h"] - a.dispatch_h) < FLOAT_TOL
                                and trips[k]["kg"] < cap - FLOAT_TOL), None)
                    new = tid is None
                    if new:
                        if trips_used[(a.vehicle_id, day)] >= veh.max_trips_day[a.vehicle_id]:
                            continue
                        tid = f"T-{a.vehicle_id}-{a.dest_id}-{day}-{len(same) + 1}"
                        trips[tid] = {"vehicle": a.vehicle_id, "dest": a.dest_id, "day": day,
                                      "dispatch_h": a.dispatch_h, "kg": 0.0}
                    kg = min(stock[b.batch_id], left_dem.get(dkey, 0.0),
                             recv_cap[a.dest_id] - recv[rkey], cap - trips[tid]["kg"])
                    if kg <= FLOAT_TOL:
                        if new:
                            del trips[tid]
                        continue
                    if new:
                        trips_used[(a.vehicle_id, day)] += 1
                    stock[b.batch_id] -= kg
                    left_dem[dkey] -= kg
                    recv[rkey] += kg
                    trips[tid]["kg"] += kg
                    p = price.get((a.dest_id, b.commodity, int(a.arrival_day)), 0.0)
                    life = a.usable_life_at_arrival_h
                    lines.append({
                        "batch_id": b.batch_id, "dest_id": a.dest_id, "vehicle_id": a.vehicle_id,
                        "trip_id": tid, "mode": a.mode, "dispatch_day": day,
                        "dispatch_h": a.dispatch_h, "arrival_h": a.arrival_h,
                        "arrival_day": int(a.arrival_day), "kg": kg,
                        "usable_life_at_arrival_h": life, "slack_h": a.slack_h,
                        "margin_inr_kg": a.margin_inr_kg,
                        # life <= 1 h (naive FIFO ships expired stock) scores as 1 h: finite JSON
                        "priority_score": kg * p / max(life, 1.0)})

        lines.sort(key=lambda r: (r["dispatch_h"], r["batch_id"], r["dest_id"], r["trip_id"]))
        for i, r in enumerate(lines, 1):
            r.update(shipment_id=f"S{i:04d}", priority_rank=i, is_frozen=False, policy=self.name)
        plan = pd.DataFrame(lines, columns=list(PLAN_COLUMNS))
        rows = []
        for tid, v in sorted(trips.items()):
            vr = veh.loc[v["vehicle"]]
            ln = lanes.loc[(vr.origin, v["dest"], vr["mode"])]
            rows.append({
                "trip_id": tid, "vehicle_id": v["vehicle"], "origin": vr.origin,
                "dest_id": v["dest"], "mode": vr["mode"], "dispatch_day": v["day"],
                "dispatch_h": v["dispatch_h"], "kg_total": v["kg"],
                "capacity_kg": vr.capacity_kg, "utilization_pct": 100.0 * v["kg"] / vr.capacity_kg,
                "cost_fixed_inr": ln.cost_fixed_inr_trip,
                "cost_var_inr": v["kg"] * ln.cost_var_inr_kg})
        return Plan(plan, pd.DataFrame(rows, columns=list(TRIP_COLUMNS)))
