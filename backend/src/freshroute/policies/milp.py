"""Allocation MILP policies (ARCHITECTURE.md sections 9, 10, 12). Model, solve and fallbacks live
in freshroute.solvers; the module constants below are read at call time and passed down."""
from __future__ import annotations

from freshroute.config import (  # noqa: F401  patched by tests, read at call time
    AGG_ARC_THRESHOLD,
    MILP_TIME_LIMIT_S,
    MIP_REL_GAP,
    OVERSHIP_SLACK,
)
from freshroute.data.io import Scenario
from freshroute.policies.base import Plan, Policy
from freshroute.solvers import milp_model
from freshroute.solvers.aggregate import plan_aggregated
from freshroute.solvers.greedy import fefo_greedy


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
            return plan_aggregated(
                scenario, ctx, self.name, ctx.get("time_limit_s", MILP_TIME_LIMIT_S),
                ctx.get("gap", MIP_REL_GAP), ctx.get("overship_slack", OVERSHIP_SLACK))
        arcs, batches, unship = milp_model.model_data(scenario)
        ov = ctx.get("demand_cap_override")
        slack = ctx.get("overship_slack", OVERSHIP_SLACK)  # sensitivity
        used = ctx.get("residual_use")  # replan: frozen trips and arrivals
        sol, info = milp_model.solve(scenario, arcs, batches, unship,
                           ctx.get("time_limit_s", MILP_TIME_LIMIT_S), ctx.get("gap", MIP_REL_GAP),
                           override=ov, overship=slack, used=used,
                           warm=ctx.get("warm_start"))
        info["fallback_used"] = sol is None
        if sol is None:
            info.update(slack_usage={}, mip_gap=None)
        # AGENTS.md rule 6: never crash. ponytail: greedy ignores C6 and replan residuals.
        x, n = fefo_greedy(scenario, arcs, batches, ov, slack, used) if sol is None else sol
        return milp_model.build_plan(scenario, arcs, x, n, info, self.name)


class MilpMarkdownPolicy(MilpPolicy):
    """milp_markdown (ARCHITECTURE.md sections 10, 12): MILP plan + tiered markdown."""

    name = "milp_markdown"

    def plan(self, scenario: Scenario, ctx: dict | None = None) -> Plan:
        from freshroute.domain.discount import build_discounts

        p = super().plan(scenario, ctx)
        p.plan["policy"] = self.name
        p.discounts = build_discounts(scenario, p.plan)
        return p
