"""FEFO-greedy baseline (ARCHITECTURE.md section 12): earliest-expiry batch first, to the
highest-margin feasible arc with capacity, same demand caps as the MILP. Reuses the MILP's
greedy fallback; never computes net INR (AGENTS.md rule 3).
"""
from __future__ import annotations

from freshroute.io import Scenario
from freshroute.policies.base import Plan, Policy
from freshroute.policies.milp import _build_plan, _greedy, _model_data


class FefoPolicy(Policy):
    name = "fefo"

    def plan(self, scenario: Scenario, ctx: dict | None = None) -> Plan:
        arcs, batches, _ = _model_data(scenario)
        x, n = _greedy(scenario, arcs, batches)
        return _build_plan(scenario, arcs, x, n, None, self.name)
