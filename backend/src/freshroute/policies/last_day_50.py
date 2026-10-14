"""last_day_50 baseline (ARCHITECTURE.md section 12): FIFO-nearest allocation plus a flat
markdown of min(LAST_DAY_DISCOUNT_PCT, max_discount_pct) once a lot's remaining life is
<= DISCOUNT_TIME_TRIGGER_H, capped at the salvage floor (discounts.csv, DATABASE.md 5.4).
"""
from __future__ import annotations

import pandas as pd

from freshroute.config import DISCOUNT_TIME_TRIGGER_H, FLOAT_TOL, LAST_DAY_DISCOUNT_PCT
from freshroute.data.io import Scenario
from freshroute.domain import costmodel as cm
from freshroute.domain.discount import COLUMNS, lots
from freshroute.policies.base import Plan, Policy
from freshroute.policies.fifo import FifoPolicy


def last_day_discounts(scenario: Scenario, plan: pd.DataFrame) -> pd.DataFrame:
    """One row per lot-day inside the last DISCOUNT_TIME_TRIGGER_H hours of usable life."""
    t = scenario.tables
    comm = t["commodities"].set_index("commodity")
    horizon = int(scenario.meta["horizon_days"])
    price = t["prices"].set_index(["dest_id", "commodity", "day"]).price_inr_kg
    rows: list[dict] = []
    if plan.empty:
        return pd.DataFrame(rows, columns=list(COLUMNS))
    for lot in lots(plan, t["batches"], t["commodities"]).itertuples():
        c = comm.loc[lot.commodity]
        for k in range(int(lot.arrival_day), min(horizon - 1, int(lot.expiry_h // 24)) + 1):
            hours_left = lot.expiry_h - max(24 * k, lot.arrival_h)
            if hours_left <= 0:
                break
            if hours_left > DISCOUNT_TIME_TRIGGER_H + FLOAT_TOL:
                continue
            p = float(price.get((lot.dest_id, lot.commodity, k), 0.0))
            cap, capped_by = 100 * c["max_discount_frac"], "max_discount"
            salvage_cap = 100 * cm.salvage_cap_frac(p, c["salvage_value_inr_kg"])
            if salvage_cap < cap - FLOAT_TOL:
                cap, capped_by = max(0.0, salvage_cap), "salvage_floor"
            if LAST_DAY_DISCOUNT_PCT <= cap + FLOAT_TOL:
                cap, capped_by = float(LAST_DAY_DISCOUNT_PCT), "none"
            # ponytail: monotone by construction unless a price drop tightens the salvage cap
            # mid-trigger; then the salvage floor wins and the validator flags NOT_MONOTONE
            d = cap
            rows.append({
                "lot_id": lot.lot_id, "dest_id": lot.dest_id, "commodity": lot.commodity,
                "batch_id": lot.batch_id, "day": k, "stock_kg": lot.stock_kg, "risk": 0.0,
                "tier_base_pct": 0.0, "tier_after_time_trigger_pct": float(LAST_DAY_DISCOUNT_PCT),
                "discount_pct": d, "capped_by": capped_by, "applied": d > 0,
                "forced_by_monotone": False, "delta_revenue_inr": 0.0})
    return pd.DataFrame(rows, columns=list(COLUMNS))


class LastDay50Policy(Policy):
    name = "last_day_50"

    def plan(self, scenario: Scenario, ctx: dict | None = None) -> Plan:
        res = FifoPolicy().plan(scenario, ctx)
        res.plan["policy"] = self.name
        res.discounts = last_day_discounts(scenario, res.plan)
        return res
