"""FEFO-greedy baseline (ARCHITECTURE.md section 12): earliest-expiry batch first, to the
highest-margin feasible arc with capacity, same demand caps as the MILP. Reuses the MILP's
greedy fallback; never computes net INR (AGENTS.md rule 3).
"""
from __future__ import annotations

from freshroute.data.io import Scenario
from freshroute.policies.base import Plan, Policy
from freshroute.solvers.greedy import fefo_greedy
from freshroute.solvers.milp_model import build_plan, model_data


class FefoPolicy(Policy):
    name = "fefo"

    def plan(self, scenario: Scenario, ctx: dict | None = None) -> Plan:
        arcs, batches, _ = model_data(scenario)
        x, n = fefo_greedy(scenario, arcs, batches)
        return build_plan(scenario, arcs, x, n, None, self.name)
