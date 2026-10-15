"""Discount ledger shape and lot construction (ARCHITECTURE.md section 10; DATABASE.md section 5.4).

`COLUMNS` is the discounts.csv schema, written by the `last_day_50` baseline and read by the
simulator, validator and reason cards; `lots` groups plan rows into per-destination lots.
FreshRoute's own policy ships no markdown (D-33).
"""
from __future__ import annotations

import pandas as pd

COLUMNS = (
    "lot_id", "dest_id", "commodity", "batch_id", "day", "stock_kg", "risk",
    "tier_base_pct", "tier_after_time_trigger_pct", "discount_pct", "capped_by",
    "applied", "forced_by_monotone", "delta_revenue_inr",
)


def lots(plan: pd.DataFrame, batches: pd.DataFrame, comm: pd.DataFrame) -> pd.DataFrame:
    p = plan.merge(batches[["batch_id", "commodity"]], on="batch_id")
    # arrival_day arrives as float when the arcs table had NaN rows; lot_id uses the int day
    p["lot_id"] = (p["batch_id"] + "@" + p["dest_id"] + "@"
                   + p["arrival_day"].astype(int).astype(str))
    keys = ["lot_id", "batch_id", "dest_id", "commodity", "arrival_day"]
    g = p.groupby(keys, as_index=False).agg(
        kg=("kg", "sum"), arrival_h=("arrival_h", "min"),
        life_h=("usable_life_at_arrival_h", "min"))
    g["expiry_h"] = g["arrival_h"] + g["life_h"]
    g = g.merge(comm[["commodity", "handling_loss_frac"]], on="commodity")
    g["stock_kg"] = g["kg"] * (1 - g["handling_loss_frac"])
    return g.sort_values(["dest_id", "commodity", "expiry_h", "lot_id"], kind="stable")
