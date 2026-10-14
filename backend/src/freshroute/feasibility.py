"""Shelf-life feasibility pre-filter: the arcs table (ARCHITECTURE.md section 8, A-01;
DATABASE.md section 4.1). Feasible and rejected arcs are both kept, with a reject_reason.
"""
from __future__ import annotations

import math

import pandas as pd

from freshroute import costmodel as cm
from freshroute.config import FLOAT_TOL, HOURS_PER_DAY
from freshroute.io import Scenario
from freshroute.shelflife import usable_life_at_arrival

REASONS = ("NO_LANE", "NOT_AVAILABLE", "RAIL_SLOT", "WINDOW", "SHELF_LIFE", "BEYOND_HORIZON")
COLUMNS = (
    "batch_id", "dest_id", "vehicle_id", "mode", "dispatch_day", "dispatch_h", "arrival_h",
    "arrival_day", "usable_life_at_arrival_h", "slack_h", "price_inr_kg", "margin_inr_kg",
    "feasible", "reject_reason",
)
_NAN = float("nan")


def _next_slot(t_h: float, slots: list[float]) -> float:
    """Earliest slot-hour-of-day departure at or after absolute hour t_h."""
    day = math.floor(t_h / HOURS_PER_DAY + FLOAT_TOL)
    for d in (day, day + 1):
        for s in slots:
            if d * HOURS_PER_DAY + s >= t_h - FLOAT_TOL:
                return float(d * HOURS_PER_DAY + s)
    raise AssertionError("unreachable: slots non-empty")  # pragma: no cover


def build_arcs(scenario: Scenario, realization: dict | None = None) -> pd.DataFrame:
    """One row per (batch, dest, vehicle, dispatch day).

    `realization` (None = base p50) may carry `rsl_h` {batch_id: h} and
    `travel_h` {(origin, dest_id, mode): h} overrides.
    """
    t = scenario.tables
    r = realization or {}
    rsl_over, travel_over = r.get("rsl_h", {}), r.get("travel_h", {})
    horizon = int(scenario.meta["horizon_days"])
    daily = scenario.meta.get("window_mode", "absolute") == "daily"
    disp_hour = scenario.dispatch_hour

    com = t["commodities"].set_index("commodity")
    dests = t["destinations"].set_index("dest_id").sort_index()
    lanes = t["lanes"].set_index(["origin", "dest_id", "mode"])
    prices = t["prices"].set_index(["dest_id", "commodity", "day"])["price_inr_kg"]
    batches = t["batches"].sort_values("batch_id")
    vehicles = t["vehicles"].sort_values("vehicle_id")

    rows = []
    for b in batches.itertuples():
        c = com.loc[b.commodity]
        rsl = rsl_over.get(b.batch_id, b.remaining_shelf_life_h)
        for dest_id, d in dests.iterrows():
            for v in vehicles.itertuples():
                for day in range(horizon):
                    row = dict.fromkeys(COLUMNS, _NAN)
                    row.update(batch_id=b.batch_id, dest_id=dest_id, vehicle_id=v.vehicle_id,
                               mode=v.mode, dispatch_day=day, feasible=False)
                    key = (v.origin, dest_id, v.mode)
                    day_end = (day + 1) * HOURS_PER_DAY
                    ready = max(b.available_from_h, v.available_from_h)
                    if b.origin_hub != v.origin or key not in lanes.index:
                        reason = "NO_LANE"
                    elif v.max_trips_day == 0 or ready >= day_end - FLOAT_TOL:
                        reason = "NOT_AVAILABLE"
                    else:
                        reason = None
                    if reason:
                        row["reject_reason"] = reason
                        rows.append(row)
                        continue
                    ln = lanes.loc[key]
                    dispatch_h = max(day * HOURS_PER_DAY + disp_hour, ready)
                    if v.mode == "rail":
                        # pandas reads a lone slot as float ("6.0")
                        slots = sorted(float(s) for s in str(ln.departure_slots).split("|"))
                        dispatch_h = _next_slot(dispatch_h, slots)
                        if dispatch_h >= day_end - FLOAT_TOL:
                            reason = "RAIL_SLOT"
                    travel = travel_over.get(key, ln.travel_h_p50)
                    arrival_h = dispatch_h + travel
                    arrival_day = int(math.floor(arrival_h / HOURS_PER_DAY + FLOAT_TOL))
                    usable = usable_life_at_arrival(
                        rsl, dispatch_h - b.available_from_h, travel, d.handling_time_h,
                        b.storage_temp_c, ln.transit_temp_c, c.ref_temp_c, c.q10)
                    slack = usable - c.min_sell_window_h
                    clock = arrival_h % HOURS_PER_DAY if daily else arrival_h
                    price = prices.get((dest_id, b.commodity, arrival_day), _NAN)
                    row.update(
                        dispatch_h=dispatch_h, arrival_h=arrival_h, arrival_day=arrival_day,
                        usable_life_at_arrival_h=usable, slack_h=slack, price_inr_kg=price,
                        margin_inr_kg=cm.shipped_margin(
                            price, c.handling_loss_frac, c.unit_cost_inr_kg,
                            ln.cost_var_inr_kg, d.handling_cost_inr_kg))
                    if reason is None and not (
                            d.window_open_h - FLOAT_TOL <= clock <= d.window_close_h + FLOAT_TOL):
                        reason = "WINDOW"
                    if reason is None and slack < -FLOAT_TOL:
                        reason = "SHELF_LIFE"
                    if reason is None and arrival_day > horizon - 1:
                        reason = "BEYOND_HORIZON"
                    row["feasible"] = reason is None
                    row["reject_reason"] = reason or ""
                    rows.append(row)
    df = pd.DataFrame(rows, columns=list(COLUMNS))
    df["feasible"] = df["feasible"].astype(bool)
    return df
