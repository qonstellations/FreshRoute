"""Newsvendor demand target (ARCHITECTURE.md section 14.3; DATABASE.md section 4.2).

Per (dest, commodity, day): q* = c_u / (c_u + c_o), clamped to NEWSVENDOR_CLAMP, then the demand
quantile from the section 14.1 piecewise-linear inverse CDF through (0.1, p10), (0.5, p50),
(0.9, p90). The MILP reads `override()` through its `demand_cap_override` hook (C5).
"""
from __future__ import annotations

import pandas as pd

from freshroute import costmodel
from freshroute.config import NEWSVENDOR_CLAMP, NEWSVENDOR_MARKDOWN_REF
from freshroute.io import Scenario

COLUMNS = ("dest_id", "commodity", "day", "target_kg", "quantile_used", "c_u", "c_o")
_KNOTS = (0.1, 0.5, 0.9)


def quantile(u: float, p10: float, p50: float, p90: float) -> float:
    """Section 14.1 (A-13) inverse CDF: linear between knots, end-segment slope beyond, >= 0."""
    if u <= _KNOTS[1]:
        v = p50 + (u - _KNOTS[1]) * (p50 - p10) / (_KNOTS[1] - _KNOTS[0])
    else:
        v = p50 + (u - _KNOTS[1]) * (p90 - p50) / (_KNOTS[2] - _KNOTS[1])
    return max(0.0, v)


def demand_target(sc: Scenario, on: bool = True) -> pd.DataFrame:
    """The demand_target table, sorted by key. `on=False` gives target_kg = demand_kg_p50."""
    t = sc.tables
    com = t["commodities"].set_index("commodity")
    dest = t["destinations"].set_index("dest_id")
    price = t["prices"].set_index(["dest_id", "commodity", "day"]).price_inr_kg
    origins = t["batches"].groupby("commodity").origin_hub.agg(set)
    lanes = t["lanes"]
    rows = []
    dem = t["demand"].sort_values(["dest_id", "commodity", "day"])
    for r in dem.itertuples(index=False):
        c = com.loc[r.commodity]
        p = price.get((r.dest_id, r.commodity, r.day))
        # cheapest lane into dest from an origin that holds this commodity
        ln = lanes[(lanes.dest_id == r.dest_id)
                   & lanes.origin.isin(origins.get(r.commodity, set()))]
        if p is None or pd.isna(p) or ln.empty:  # unreachable or unpriced: target unused
            rows.append((r.dest_id, r.commodity, r.day, float(r.demand_kg_p50), 0.5,
                         float("nan"), float("nan")))
            continue
        c_u = costmodel.shipped_margin(p, c.handling_loss_frac, c.unit_cost_inr_kg,
                                       float(ln.cost_var_inr_kg.min()),
                                       dest.handling_cost_inr_kg[r.dest_id])
        c_o = (costmodel.spoilage_unit_cost(c.unit_cost_inr_kg, c.disposal_cost_inr_kg,
                                            c.salvage_value_inr_kg)
               + p * NEWSVENDOR_MARKDOWN_REF)
        if not on:
            q, kg = 0.5, float(r.demand_kg_p50)
        elif c_u <= 0:
            q, kg = 0.0, 0.0
        else:
            q = min(max(c_u / (c_u + c_o), NEWSVENDOR_CLAMP[0]), NEWSVENDOR_CLAMP[1])
            kg = quantile(q, r.demand_kg_p10, r.demand_kg_p50, r.demand_kg_p90)
        rows.append((r.dest_id, r.commodity, r.day, kg, q, float(c_u), float(c_o)))
    return pd.DataFrame(rows, columns=list(COLUMNS))


def override(target: pd.DataFrame) -> dict:
    """{(dest_id, commodity, day): target_kg} for the MILP's demand_cap_override hook."""
    return {(d, c, int(day)): float(kg) for d, c, day, kg
            in target[["dest_id", "commodity", "day", "target_kg"]].itertuples(index=False)}
