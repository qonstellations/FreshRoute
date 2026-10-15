"""Reason-card text templates (ARCHITECTURE.md section 15; card fields in DATABASE.md 5.9).

`build_cards` assembles one card per plan shipment from the plan, the feasibility arcs and
discounts.csv; `render_text` only renders numbers already on a card. Read-only: nothing
here changes a plan or a KPI.
"""
from __future__ import annotations

import math
from dataclasses import replace

import pandas as pd

from freshroute.config import FLOAT_TOL
from freshroute.data.io import Scenario
from freshroute.domain.feasibility import build_arcs

# arc reject_reason -> card reason_code (DATABASE.md 5.9). NO_LANE / NOT_AVAILABLE arcs do not
# exist physically and are never offered as alternatives.
_ARC_REASON = {"SHELF_LIFE": "SHELF_LIFE", "WINDOW": "WINDOW", "BEYOND_HORIZON": "WINDOW",
               "RAIL_SLOT": "CAPACITY_BOUND"}

# reason_code -> phrase about the runner-up `a` (an alternatives[] entry)
_PHRASES = {
    "SHELF_LIFE": lambda a: (f"it would reach {a['dest_id']} with only "
                             f"{_n(a['usable_life_at_arrival_h'])} h of shelf life left, "
                             "too little to sell"),
    "WINDOW": lambda a: f"it would arrive at {a['dest_id']} outside its receiving hours",
    "CAPACITY_BOUND": lambda a: f"no truck or unloading space is left for {a['dest_id']}",
    "DEMAND_CAP": lambda a: f"{a['dest_id']} is already fully supplied",
    "LOWER_MARGIN": lambda a: (f"{a['dest_id']} earns less per kg "
                               f"(₹{a['margin_inr_kg']:.2f}/kg)"),
}


def fmt_num(x: float, ndigits: int | None = None) -> str:
    """Compact number text: general format, optionally rounded to ndigits first."""
    return f"{x if ndigits is None else round(x, ndigits):g}"


def _n(x: float) -> str:
    return fmt_num(x)


def render_text(card: dict) -> str:
    """Plain-text reason for one shipment card (DATABASE.md 5.9)."""
    c = card["chosen"]
    alts = card.get("alternatives") or []
    head = f"Sent to {c['dest_id']}"
    if alts:
        a = alts[0]
        head += f", not {a['dest_id']}: {_PHRASES[a['reason_code']](a)}"
    text = (f"{head}; {_n(c['usable_life_at_arrival_h'])} h of shelf life left on arrival, "
            f"{_n(c['slack_h'])} h to spare, earns ₹{c['margin_inr_kg']:.2f}/kg. "
            f"Loading priority #{card['priority']['rank']}.")
    d = card.get("discount")
    if d is not None:
        text += (f" Price cut: {d['tier_pct']} % off from day {d['day']} "
                 f"(risk of not selling {d['risk']:.2f})")
        text += f", limited by {d['capped_by']}." if d.get("capped_by", "none") != "none" else "."
    return text


def _f(x) -> float | None:
    """JSON-safe float (NaN / +-inf -> null)."""
    return None if x is None or pd.isna(x) or not math.isfinite(x) else float(x)


def _scoped_arcs(scenario: Scenario, plan: pd.DataFrame) -> pd.DataFrame:
    """Arcs for reason cards on a scoped sub-scenario.

    Only batches in ``plan`` are looked up (``by_batch.get(batch)`` below), and
    vehicles sharing ``(origin, mode, available_from_h)`` have identical arcs
    (A-46), so one representative vehicle per class suffices. Alternatives carry
    no ``vehicle_id`` (DATABASE.md 5.9), so the representative choice is
    invisible in the output. Destinations stay unfiltered: every batch needs
    every destination as a candidate alternative.
    """
    t = scenario.tables
    batches = t["batches"][t["batches"].batch_id.isin(set(plan.batch_id))].copy()
    vehicles = t["vehicles"].sort_values("vehicle_id")
    reps = vehicles.groupby(["origin", "mode", "available_from_h"], sort=True).head(1)
    sub = replace(scenario, tables={**t, "batches": batches, "vehicles": reps})
    return build_arcs(sub)


def build_cards(scenario: Scenario, plan: pd.DataFrame, discounts: pd.DataFrame,
                arcs: pd.DataFrame | None = None) -> list[dict]:
    """reason_cards.json (DATABASE.md 5.9): one card per shipment, sorted by shipment_id.

    ``arcs`` overrides the internally built table (callers with arcs on hand may
    pass them); otherwise only the scoped arcs needed for this plan are built.
    """
    if len(plan) == 0:
        return []
    t = scenario.tables
    commodity = dict(zip(t["batches"].batch_id, t["batches"].commodity, strict=True))
    demand = t["demand"].set_index(["dest_id", "commodity", "day"])["demand_kg_p50"].to_dict()
    shipped = plan.assign(commodity=plan.batch_id.map(commodity)).groupby(
        ["dest_id", "commodity", "arrival_day"]).kg.sum().to_dict()

    arcs = _scoped_arcs(scenario, plan) if arcs is None else arcs
    arcs = arcs[~arcs.reject_reason.isin(["NO_LANE", "NOT_AVAILABLE"])]
    # best arc per (batch, dest, mode): feasible first, then margin, slack, earliest, vehicle
    best = (arcs.sort_values(["batch_id", "dest_id", "mode", "feasible", "margin_inr_kg",
                              "slack_h", "dispatch_day", "vehicle_id"],
                             ascending=[True, True, True, False, False, False, True, True],
                             na_position="last", kind="stable")
            .drop_duplicates(["batch_id", "dest_id", "mode"]))
    by_batch = dict(tuple(best.groupby("batch_id", sort=True)))

    disc = discounts[discounts.applied.astype(bool) & (discounts.discount_pct > FLOAT_TOL)]
    disc = disc.sort_values(["lot_id", "day"], kind="stable").drop_duplicates("lot_id")
    disc = {d.lot_id: d for d in disc.itertuples()}

    cards = []
    for r in plan.sort_values("shipment_id", kind="stable").itertuples():
        com = commodity[r.batch_id]
        cand = by_batch.get(r.batch_id, best.iloc[0:0])
        alts = []
        for a in cand[cand.dest_id != r.dest_id].itertuples():
            if not a.feasible:
                code = _ARC_REASON[a.reject_reason]
            elif a.margin_inr_kg < r.margin_inr_kg - FLOAT_TOL:
                code = "LOWER_MARGIN"
            elif (shipped.get((a.dest_id, com, a.arrival_day), 0.0)
                  >= demand.get((a.dest_id, com, a.arrival_day), 0.0) - FLOAT_TOL):
                code = "DEMAND_CAP"
            else:
                code = "CAPACITY_BOUND"
            alts.append({
                "dest_id": a.dest_id, "mode": a.mode, "dispatch_day": int(a.dispatch_day),
                "feasible": bool(a.feasible), "reject_reason": a.reject_reason,
                "usable_life_at_arrival_h": _f(a.usable_life_at_arrival_h),
                "slack_h": _f(a.slack_h), "margin_inr_kg": _f(a.margin_inr_kg),
                "margin_delta_inr_kg": _f(r.margin_inr_kg - a.margin_inr_kg),
                "slack_delta_h": _f(r.slack_h - a.slack_h), "reason_code": code})
        # runner-up first: feasible, then highest margin
        alts.sort(key=lambda x: (not x["feasible"], x["margin_inr_kg"] is None,
                                 -(x["margin_inr_kg"] or 0.0),
                                 x["dest_id"], x["mode"]))
        ru = alts[0] if alts else None
        d = disc.get(f"{r.batch_id}@{r.dest_id}@{int(r.arrival_day)}")
        card = {
            "shipment_id": r.shipment_id, "batch_id": r.batch_id, "commodity": com,
            "chosen": {"dest_id": r.dest_id, "vehicle_id": r.vehicle_id, "mode": r.mode,
                       "dispatch_h": _f(r.dispatch_h), "arrival_h": _f(r.arrival_h),
                       "kg": _f(r.kg), "usable_life_at_arrival_h": _f(r.usable_life_at_arrival_h),
                       "slack_h": _f(r.slack_h), "margin_inr_kg": _f(r.margin_inr_kg)},
            "priority": {"rank": int(r.priority_rank), "score": _f(r.priority_score)},
            "alternatives": alts,
            "runner_up": None if ru is None else {
                "dest_id": ru["dest_id"], "reason_code": ru["reason_code"],
                "margin_delta_inr_kg": ru["margin_delta_inr_kg"],
                "margin_delta_inr": None if ru["margin_delta_inr_kg"] is None
                else float(r.kg * ru["margin_delta_inr_kg"]),
                "slack_delta_h": ru["slack_delta_h"]},
            "discount": None if d is None else {
                "day": int(d.day), "risk": _f(d.risk), "tier_pct": _f(d.discount_pct),
                "capped_by": d.capped_by},
        }
        card["text"] = render_text(card)
        cards.append(card)
    return cards
