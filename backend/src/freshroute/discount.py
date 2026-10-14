"""Disclosed tiered markdown rule (ARCHITECTURE.md section 10; DATABASE.md section 5.4).

Tier/time-trigger/cap/worth-it logic is pure (`discount_pct`); `build_discounts` only
walks lots in FEFO order and feeds it. Parameters live in config.py / the dataset.
"""
from __future__ import annotations

from typing import NamedTuple

import pandas as pd

from freshroute import costmodel as cm
from freshroute.config import (
    DISCOUNT_RISK_BREAKS,
    DISCOUNT_TIERS_PCT,
    DISCOUNT_TIME_TRIGGER_H,
    FLOAT_TOL,
)

COLUMNS = (
    "lot_id", "dest_id", "commodity", "batch_id", "day", "stock_kg", "risk",
    "tier_base_pct", "tier_after_time_trigger_pct", "discount_pct", "capped_by",
    "applied", "forced_by_monotone", "delta_revenue_inr",
)


class Decision(NamedTuple):
    tier_base_pct: float
    tier_after_time_trigger_pct: float
    discount_pct: float
    capped_by: str  # none / max_discount / salvage_floor
    applied: bool
    delta_revenue_inr: float


def tier_index(risk: float) -> int:
    """Tier index from risk (A-22: exactly the 2nd and 3rd break stay in the lower tier)."""
    n = len(DISCOUNT_RISK_BREAKS)
    idx = 0
    for i, b in enumerate(DISCOUNT_RISK_BREAKS):
        # last break is strict (risk > 0.50 -> top tier); the others are inclusive on the
        # low side, except A-22 puts exactly 0.30 in the 20 % tier, which >= already gives.
        hit = risk > b + FLOAT_TOL if i == n - 1 else risk >= b - FLOAT_TOL
        if hit:
            idx = i + 1
    return idx


def delta_revenue(
    stock_kg: float, demand_kg: float, price: float, eps: float, frac: float,
) -> float:
    """Worth-it test value (ARCH section 10 step 5)."""
    base = min(stock_kg, demand_kg)
    extra = min(stock_kg, demand_kg * cm.demand_uplift(eps, frac)) - base
    return extra * price * (1 - frac) - base * price * frac


def discount_pct(
    risk: float, hours_left: float, *, stock_kg: float, demand_kg: float, price: float,
    elasticity: float, salvage: float, max_discount_frac: float,
) -> Decision:
    """Markdown % for one lot on one day (before the monotone step)."""
    i = tier_index(risk)
    base = DISCOUNT_TIERS_PCT[i]
    near_end = hours_left <= DISCOUNT_TIME_TRIGGER_H + FLOAT_TOL
    j = min(i + 1, len(DISCOUNT_TIERS_PCT) - 1) if near_end else i
    trig = DISCOUNT_TIERS_PCT[j]
    cap_frac, capped_by = max_discount_frac, "max_discount"
    salvage_cap = cm.salvage_cap_frac(price, salvage)
    if salvage_cap < cap_frac - FLOAT_TOL:
        cap_frac, capped_by = salvage_cap, "salvage_floor"
    cap = max(0.0, cap_frac * 100)
    top = min(trig, cap)
    if trig <= cap + FLOAT_TOL:
        capped_by = "none"
    # candidates: capped proposed tier, then each lower tier
    cands = [top] + [t for t in reversed(DISCOUNT_TIERS_PCT[:j]) if t < top - FLOAT_TOL]
    chosen, dr = 0.0, 0.0
    for c in cands:
        if c <= 0:
            break
        d = delta_revenue(stock_kg, demand_kg, price, elasticity, c / 100)
        if d > FLOAT_TOL:
            chosen, dr = float(c), d
            break
    return Decision(base, trig, chosen, capped_by, chosen > 0, dr)


def _lots(plan: pd.DataFrame, batches: pd.DataFrame, comm: pd.DataFrame) -> pd.DataFrame:
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


def build_discounts(scenario, plan: pd.DataFrame) -> pd.DataFrame:
    """discounts.csv rows (one per lot-day) using p50 demand and FEFO residual demand."""
    t = scenario.tables
    comm = t["commodities"].set_index("commodity")
    horizon = int(scenario.meta.get("horizon_days", 1))
    resid = dict(t["demand"].set_index(["dest_id", "commodity", "day"])["demand_kg_p50"].items())
    pr = t["prices"].sort_values("day")
    prices = {
        k: g.set_index("day")["price_inr_kg"] for k, g in pr.groupby(["dest_id", "commodity"])
    }
    rows: list[dict] = []
    if plan.empty:
        return pd.DataFrame(rows, columns=list(COLUMNS))
    for lot in _lots(plan, t["batches"], t["commodities"]).itertuples():
        c = comm.loc[lot.commodity]
        a, last = int(lot.arrival_day), min(horizon - 1, int(lot.expiry_h // 24))
        days = range(a, last + 1)
        ds = {k: resid.get((lot.dest_id, lot.commodity, k), 0.0) for k in days}
        ser = prices[(lot.dest_id, lot.commodity)]
        prev = 0.0
        for k in days:
            hours_left = lot.expiry_h - max(24 * k, lot.arrival_h)
            if hours_left <= 0:
                break
            demand = sum(ds[d] for d in range(k, last + 1))
            risk = 1 - min(1.0, demand / lot.stock_kg) if lot.stock_kg > 0 else 0.0
            price = float(ser[ser.index <= k].iloc[-1])
            d = discount_pct(
                risk, hours_left, stock_kg=lot.stock_kg, demand_kg=demand, price=price,
                elasticity=c["price_elasticity"], salvage=c["salvage_value_inr_kg"],
                max_discount_frac=c["max_discount_frac"])
            final, forced, dr = d.discount_pct, False, d.delta_revenue_inr
            if prev > final + FLOAT_TOL:  # monotone: never decrease over time
                final = prev
                dr = delta_revenue(lot.stock_kg, demand, price, c["price_elasticity"], final / 100)
                forced = dr <= FLOAT_TOL
            prev = final
            rows.append({
                "lot_id": lot.lot_id, "dest_id": lot.dest_id, "commodity": lot.commodity,
                "batch_id": lot.batch_id, "day": k, "stock_kg": lot.stock_kg, "risk": risk,
                "tier_base_pct": d.tier_base_pct,
                "tier_after_time_trigger_pct": d.tier_after_time_trigger_pct,
                "discount_pct": final, "capped_by": d.capped_by, "applied": final > 0,
                "forced_by_monotone": forced, "delta_revenue_inr": dr})
        left = lot.stock_kg
        for k in days:  # lot consumes earliest demand first; later lots see the residual
            take = min(left, ds[k])
            resid[(lot.dest_id, lot.commodity, k)] = ds[k] - take
            left -= take
    return pd.DataFrame(rows, columns=list(COLUMNS))
