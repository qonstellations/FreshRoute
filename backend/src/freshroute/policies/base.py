"""Policy interface and Plan container (ARCHITECTURE.md section 9, DATABASE.md 5.2-5.3).

A policy returns allocations only; the simulator alone reports net INR (AGENTS.md rule 3).
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from freshroute.io import Scenario

PLAN_COLUMNS = (
    "shipment_id", "batch_id", "dest_id", "vehicle_id", "trip_id", "mode", "dispatch_day",
    "dispatch_h", "arrival_h", "arrival_day", "kg", "usable_life_at_arrival_h", "slack_h",
    "margin_inr_kg", "priority_rank", "priority_score", "is_frozen", "policy",
)
TRIP_COLUMNS = (
    "trip_id", "vehicle_id", "origin", "dest_id", "mode", "dispatch_day", "dispatch_h",
    "kg_total", "capacity_kg", "utilization_pct", "cost_fixed_inr", "cost_var_inr",
)


@dataclass
class Plan:
    plan: pd.DataFrame  # plan.csv
    trips: pd.DataFrame  # trips.csv
    solver: dict | None = None  # manifest "solver" block; None for non-MILP policies
    discounts: pd.DataFrame | None = None  # discounts.csv (DATABASE.md 5.4); None = no markdown


class Policy:
    name = "base"

    def plan(self, scenario: Scenario, ctx: dict | None = None) -> Plan:
        raise NotImplementedError
