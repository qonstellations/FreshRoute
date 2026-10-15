"""Robust MILP policy (ARCHITECTURE.md section 14.5, A-52): plan on pessimistic inputs
(P10 shelf life, P90 travel), then re-time the chosen shipments on the base (p50) arcs so
the simulator and validator measure it like every other policy (AGENTS.md rule 3).
"""
from __future__ import annotations

import copy

from freshroute.data.io import Scenario
from freshroute.domain.feasibility import build_arcs
from freshroute.policies.base import PLAN_COLUMNS, Plan
from freshroute.policies.milp import MilpPolicy

KEYS = ["batch_id", "dest_id", "vehicle_id", "dispatch_day"]
RETIME = ["mode", "dispatch_h", "arrival_h", "arrival_day", "usable_life_at_arrival_h",
          "slack_h", "margin_inr_kg"]


def pessimistic(sc: Scenario) -> Scenario:
    """Copy of `sc` with every batch at its P10 shelf life and every lane at its P90 travel."""
    s = copy.deepcopy(sc)
    b, ln = s.tables["batches"], s.tables["lanes"]
    b["remaining_shelf_life_h"] = b["rsl_p10_h"].astype(float)
    ln["travel_h_p50"] = ln["travel_h_p90"].astype(float)
    return s


class MilpRobustPolicy(MilpPolicy):
    name = "milp_robust"

    def plan(self, scenario: Scenario, ctx: dict | None = None) -> Plan:
        res = super().plan(pessimistic(scenario), {k: v for k, v in (ctx or {}).items()
                                                   if k != "on_plan"})
        base = build_arcs(scenario)
        base = base[base.feasible][KEYS + RETIME]
        # a line feasible at P10/P90 is feasible at p50 too; inner merge drops any that is not
        p = res.plan.drop(columns=RETIME).merge(base, on=KEYS, how="inner")
        disp = p.groupby("trip_id").dispatch_h.max()
        trips = res.trips[res.trips.trip_id.isin(disp.index)].copy()
        trips["dispatch_h"] = trips.trip_id.map(disp)
        res.solver = {**(res.solver or {}), "robust": {
            "rsl": "rsl_p10_h", "travel": "travel_h_p90",
            "dropped_lines": int(len(res.plan) - len(p))}}
        return Plan(p.reindex(columns=list(PLAN_COLUMNS)), trips, res.solver, res.discounts)
