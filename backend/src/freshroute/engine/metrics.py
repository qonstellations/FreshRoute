"""Aggregate a simulated plan into metrics.json (ARCHITECTURE.md sections 7 and 13;
DATABASE.md section 5.7). Reads only; all money goes through costmodel.py.

Inputs (plain pandas, so simulator.py can be built independently):
  scenario  : object with .tables (dict of DataFrames per schema.py) and .meta (dict, "name").
  plan      : plan.csv DataFrame (DATABASE 5.2): batch_id, dest_id, trip_id, vehicle_id, mode, kg.
  discounts : discounts.csv DataFrame (DATABASE 5.4). Accepted for the contract; the applied
              discount per day is already in sim["ledger"], which is what gets priced.
  sim       : dict
      "ledger"  DataFrame, one row per (dest_id, commodity, day), columns:
                base_demand_kg, delivered_kg, handling_loss_kg, sold_kg, price_inr_kg,
                discount_frac (0-1), unsold_expired_kg, carryover_kg (alive at horizon end)
      "origin"  DataFrame, one row per batch with unshipped stock: batch_id, expired_kg,
                carryover_kg
      optional: "violations" (int, from validator), "run_id", "policy", "seed", "realization"
"""
from __future__ import annotations

import pandas as pd

from freshroute.config import SCHEMA_VERSION
from freshroute.data.io import Scenario
from freshroute.domain import costmodel as cm


def _pct(num: float, den: float) -> float:
    return 100.0 * num / den if den > 0 else 0.0


def compute(scenario: Scenario, plan: pd.DataFrame, discounts: pd.DataFrame, sim: dict) -> dict:
    t = scenario.tables
    led = sim["ledger"].copy()
    org = sim["origin"].copy()
    batches = t["batches"].set_index("batch_id")
    com = t["commodities"].set_index("commodity")

    supply = float(batches["qty_kg"].sum())
    shipped = float(plan["kg"].sum())

    # --- economics (all via costmodel) ---
    gross = float(cm.gross_revenue_at_list(led.sold_kg, led.price_inr_kg).sum())
    disc = float(cm.discount_cost(led.sold_kg, led.price_inr_kg, led.discount_frac).sum())
    rev = float(cm.revenue(led.sold_kg, led.price_inr_kg, led.discount_frac).sum())

    p = plan.copy()
    p["origin"] = p["batch_id"].map(batches["origin_hub"])
    p = p.merge(t["lanes"], on=["origin", "dest_id", "mode"], how="left")
    trips = p.groupby("trip_id", sort=True).agg(
        kg=("kg", "sum"), fixed=("cost_fixed_inr_trip", "first"),
        var=("cost_var_inr_kg", "first"), vehicle_id=("vehicle_id", "first"))
    transport = float(cm.transport(1, trips.fixed, trips.kg, trips["var"]).sum())
    util = trips.kg / trips.vehicle_id.map(t["vehicles"].set_index("vehicle_id")["capacity_kg"])

    hc = led.dest_id.map(t["destinations"].set_index("dest_id")["handling_cost_inr_kg"])
    handling = float(cm.handling(led.delivered_kg, hc).sum())

    # spoiled kg by commodity (delivered side + origin side), priced per commodity
    org["commodity"] = org["batch_id"].map(batches["commodity"])
    led["spoiled_kg"] = led.handling_loss_kg + led.unsold_expired_kg
    sp_com = led.groupby("commodity").spoiled_kg.sum().add(
        org.groupby("commodity").expired_kg.sum(), fill_value=0.0)
    sp_cost = float(cm.spoilage(
        sp_com, com.loc[sp_com.index, "unit_cost_inr_kg"],
        com.loc[sp_com.index, "disposal_cost_inr_kg"],
        com.loc[sp_com.index, "salvage_value_inr_kg"]).sum())
    sold_by_com = led.groupby("commodity").sold_kg.sum()
    cogs = float(cm.cost_of_goods_sold(
        sold_by_com, com.loc[sold_by_com.index, "unit_cost_inr_kg"]).sum())
    net = float(cm.net(rev, cogs, transport, handling, sp_cost))

    # --- volumes ---
    hl = float(led.handling_loss_kg.sum())
    due = float(led.unsold_expired_kg.sum())
    oe = float(org.expired_kg.sum())
    spoil = hl + due + oe
    sold = float(led.sold_kg.sum())
    co_d, co_o = float(led.carryover_kg.sum()), float(org.carryover_kg.sum())

    # --- fulfillment: sum min(sold, base_demand) / sum base_demand ---
    led["met_kg"] = led[["sold_kg", "base_demand_kg"]].min(axis=1)
    g = led.groupby("dest_id")
    fill = (g.met_kg.sum() / g.base_demand_kg.sum().where(lambda s: s > 0)).fillna(1.0) * 100.0

    supply_com = batches.groupby("commodity").qty_kg.sum()
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": sim.get("run_id", ""),
        "scenario": scenario.meta.get("name", ""),
        "policy": sim.get("policy", ""),
        "seed": sim.get("seed"),
        "realization": sim.get("realization", "base"),
        "kpis": {
            "spoilage_kg": spoil, "spoilage_pct": _pct(spoil, supply),
            "demand_fulfillment_pct": _pct(led.met_kg.sum(), led.base_demand_kg.sum()),
            "min_dest_fill_pct": float(fill.min()) if len(fill) else 0.0,
            "net_inr": net, "violations": int(sim.get("violations", 0)),
        },
        "spoilage_breakdown_kg": {
            "handling_loss": hl, "delivered_unsold_expired": due, "origin_expired": oe},
        "economics_inr": {
            "gross_revenue_at_list": gross, "discount_cost": disc, "revenue": rev,
            "cost_of_goods_sold": cogs, "transport": transport, "handling": handling,
            "spoilage_cost": sp_cost, "net": net},
        "volumes_kg": {
            "total_supply": supply, "shipped": shipped, "unshipped": supply - shipped,
            "sold": sold,
            "carryover": {"destination": co_d, "origin": co_o, "total": co_d + co_o}},
        "trips": {"count": len(trips),
                  "avg_utilization_pct": 100.0 * float(util.mean()) if len(util) else 0.0},
        "per_destination": [
            {"dest_id": d, "fill_pct": float(fill[d]), "sold_kg": float(r.sold_kg),
             "spoiled_kg": float(r.spoiled_kg)}
            for d, r in g[["sold_kg", "spoiled_kg"]].sum().iterrows()],
        "per_commodity": [
            {"commodity": c, "spoilage_kg": float(k),
             "spoilage_pct": _pct(k, float(supply_com.get(c, 0.0))),
             "sold_kg": float(sold_by_com.get(c, 0.0))}
            for c, k in sp_com.sort_index().items()],
    }
