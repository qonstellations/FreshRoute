"""Day-bucket simulator (ARCHITECTURE.md section 13; D-07, D-08, A-04..A-06).

Executes a plan against a realization and returns the `sim` dict that metrics.compute
consumes: `ledger`, `origin`, plus `lots` (simlots.csv). It never enforces windows or
capacities (the validator's job). All coefficients come from the scenario tables / config.
"""
from __future__ import annotations

import math

import pandas as pd

from freshroute.config import FLOAT_TOL
from freshroute.domain import costmodel as cm
from freshroute.domain import discount
from freshroute.domain.shelflife import decay, usable_life_at_arrival


def _price(ser: pd.Series | None, day: int) -> float:
    if ser is None or not (ser.index <= day).any():
        return 0.0
    return float(ser[ser.index <= day].iloc[-1])


def _realize(scenario, plan: pd.DataFrame, discounts: pd.DataFrame, real: dict):
    """Re-time plan lines under sampled `travel_h` / `rsl_h` (ARCH 14.1, A-42): same dispatch,
    new arrival and usable life (section 7). Discount rows follow their lot to its new id."""
    if plan.empty or not (real.get("travel_h") or real.get("rsl_h")):
        return plan, discounts
    t = scenario.tables
    b = t["batches"].set_index("batch_id").loc[plan["batch_id"]]
    c = t["commodities"].set_index("commodity").loc[b["commodity"]]
    lane_key = list(zip(b["origin_hub"], plan["dest_id"], plan["mode"], strict=True))
    lanes = t["lanes"].set_index(["origin", "dest_id", "mode"])["transit_temp_c"]
    tr, rsl = real.get("travel_h", {}), real.get("rsl_h", {})
    # default travel = the plan's own (p50); a line with no lane keeps its planned timing
    travel = [tr.get(k, a - d) for k, a, d in
              zip(lane_key, plan["arrival_h"], plan["dispatch_h"], strict=True)]
    life = [
        usable_life_at_arrival(rsl.get(bid, r), dh - af, tv, hh, st, lanes[k], ref, q)
        if k in lanes.index else ul
        for bid, r, dh, af, tv, hh, st, k, ref, q, ul in zip(
            plan["batch_id"], b["remaining_shelf_life_h"], plan["dispatch_h"],
            b["available_from_h"], travel,
            plan["dest_id"].map(t["destinations"].set_index("dest_id")["handling_time_h"]),
            b["storage_temp_c"], lane_key, c["ref_temp_c"], c["q10"],
            plan["usable_life_at_arrival_h"], strict=True)]
    p = plan.copy()
    old = p["arrival_day"].astype(int)
    p["arrival_h"] = p["dispatch_h"] + travel
    p["usable_life_at_arrival_h"] = life
    p["arrival_day"] = [math.floor(a / 24 + FLOAT_TOL) for a in p["arrival_h"]]
    if discounts is not None and not discounts.empty:
        # ponytail: two old lots landing on one new lot share its last discount row
        stem = p.batch_id + "@" + p.dest_id + "@"
        ids = dict(zip(stem + old.astype(str), stem + p.arrival_day.astype(str), strict=True))
        discounts = discounts.assign(lot_id=discounts.lot_id.map(ids).fillna(discounts.lot_id))
    return p, discounts


def simulate(scenario, plan: pd.DataFrame, discounts: pd.DataFrame, realization=None) -> dict:
    """realization: None = base (p50 demand, plan's own arrival/life), or a dict with optional
    "demand_kg": {(dest_id, commodity, day): kg}, "travel_h": {(origin, dest_id, mode): h} and
    "rsl_h": {batch_id: h} overrides (A-28, A-42)."""
    t = scenario.tables
    horizon = int(scenario.meta.get("horizon_days", 1))
    comm = t["commodities"].set_index("commodity")
    batches = t["batches"].set_index("batch_id")
    real = realization or {}
    plan, discounts = _realize(scenario, plan, discounts, real)
    rsl_over = real.get("rsl_h", {})

    demand = dict(t["demand"].set_index(["dest_id", "commodity", "day"])["demand_kg_p50"].items())
    demand.update(real.get("demand_kg", {}))
    price_ser = {k: g.sort_values("day").set_index("day")["price_inr_kg"]
                 for k, g in t["prices"].groupby(["dest_id", "commodity"])}
    # discounts.csv is in pct (0-100); the shelf label is the FEFO-head lot's row (D-08)
    disc = {} if discounts is None or discounts.empty else {
        (r.lot_id, int(r.day)): r.discount_pct / 100.0 for r in discounts.itertuples()}

    lots, transit = [], []  # transit = arrives after the horizon
    if not plan.empty:
        for r in discount.lots(plan, t["batches"], t["commodities"]).itertuples():
            lot = {"lot_id": r.lot_id, "batch_id": r.batch_id, "dest_id": r.dest_id,
                   "commodity": r.commodity, "arrival_h": r.arrival_h,
                   "arrival_day": int(r.arrival_day), "expiry_h": r.expiry_h,
                   "kg_arrived": r.kg, "kg_handling_loss": r.kg - r.stock_kg,
                   "left": r.stock_kg, "kg_sold": 0.0, "kg_expired_unsold": 0.0,
                   "kg_carryover": 0.0}
            (lots if lot["arrival_day"] < horizon else transit).append(lot)

    pairs = sorted({(d, c) for d, c, _ in demand} | {(x["dest_id"], x["commodity"]) for x in lots})
    rows = []
    for dest, com in pairs:
        eps = comm.loc[com, "price_elasticity"]
        pl = sorted((x for x in lots if (x["dest_id"], x["commodity"]) == (dest, com)),
                    key=lambda x: (x["expiry_h"], x["lot_id"]))
        for k in range(horizon):
            arr = [x for x in pl if x["arrival_day"] == k]
            sellable = [x for x in pl if x["arrival_day"] <= k and x["expiry_h"] > 24 * k
                        and x["left"] > FLOAT_TOL]
            frac = disc.get((sellable[0]["lot_id"], k), 0.0) if sellable else 0.0
            base = float(demand.get((dest, com, k), 0.0))
            eff = base * cm.demand_uplift(eps, frac)
            rem = eff
            for x in sellable:  # FEFO
                take = min(x["left"], rem)
                x["left"] -= take
                x["kg_sold"] += take
                rem -= take
            expired = 0.0
            for x in pl:
                if x["arrival_day"] <= k and x["expiry_h"] <= 24 * (k + 1) and x["left"] > 0:
                    expired += x["left"]
                    x["kg_expired_unsold"] += x["left"]
                    x["left"] = 0.0
            on_hand = sum(x["left"] for x in pl if x["arrival_day"] <= k)
            carry = 0.0
            if k == horizon - 1:  # A-06: alive at horizon end, valued 0
                carry = on_hand
                for x in pl:
                    x["kg_carryover"] = x["left"]
            rows.append({
                "dest_id": dest, "commodity": com, "day": k, "base_demand_kg": base,
                "effective_demand_kg": eff, "delivered_kg": sum(x["kg_arrived"] for x in arr),
                "handling_loss_kg": sum(x["kg_handling_loss"] for x in arr),
                "sold_kg": eff - rem, "price_inr_kg": _price(price_ser.get((dest, com)), k),
                "discount_frac": frac, "unsold_expired_kg": expired,
                "on_hand_end_kg": on_hand, "carryover_kg": carry})

    shipped = plan.groupby("batch_id")["kg"].sum() if not plan.empty else pd.Series(dtype=float)
    org = []
    for bid, b in batches.sort_index().iterrows():
        un = max(0.0, b["qty_kg"] - float(shipped.get(bid, 0.0)))
        c = comm.loc[b["commodity"]]
        exp_h = b["available_from_h"] + rsl_over.get(bid, b["remaining_shelf_life_h"]) / decay(
            b["storage_temp_c"], c["ref_temp_c"], c["q10"])
        # stock still in transit at horizon end is treated like origin stock (mass balance)
        un += sum(x["kg_arrived"] for x in transit if x["batch_id"] == bid)
        gone = exp_h <= 24 * horizon
        org.append({"batch_id": bid, "kg_unshipped": un, "origin_expiry_h": exp_h,
                    "expired_kg": un if gone else 0.0, "carryover_kg": 0.0 if gone else un})

    lot_cols = ["lot_id", "dest_id", "commodity", "arrival_h", "arrival_day", "expiry_h",
                "kg_arrived", "kg_handling_loss", "kg_sold", "kg_expired_unsold", "kg_carryover"]
    return {
        "ledger": pd.DataFrame(rows),
        "origin": pd.DataFrame(org),
        "lots": pd.DataFrame([{c: x[c] for c in lot_cols} for x in lots], columns=lot_cols),
        "seed": scenario.meta.get("seed"),
        "realization": "base" if realization is None else "custom",
    }
