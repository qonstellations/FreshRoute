"""Reason-card text templates (ARCHITECTURE.md section 15; card fields in DATABASE.md 5.9).

Only renders text from a card dict that already holds the numbers; building cards from a
plan is U-01. No number is computed here.
"""
from __future__ import annotations

# reason_code -> phrase about the runner-up `a` (an alternatives[] entry)
_PHRASES = {
    "SHELF_LIFE": lambda a: (f"{a['dest_id']} arrival leaves {_n(a['usable_life_at_arrival_h'])} h"
                             " of life, below the sell window"),
    "WINDOW": lambda a: f"{a['dest_id']} arrival misses its receiving window",
    "CAPACITY_BOUND": lambda a: f"no vehicle or receiving capacity left for {a['dest_id']}",
    "DEMAND_CAP": lambda a: f"{a['dest_id']} demand is already covered",
    "LOWER_MARGIN": lambda a: (f"{a['dest_id']} earns a lower margin "
                               f"(₹{a['margin_inr_kg']:.2f}/kg)"),
}


def _n(x: float) -> str:
    return f"{x:g}"


def render_text(card: dict) -> str:
    """Plain-text reason for one shipment card (DATABASE.md 5.9)."""
    c = card["chosen"]
    alts = card.get("alternatives") or []
    head = f"Sent to {c['dest_id']}"
    if alts:
        a = alts[0]
        head += f", not {a['dest_id']}: {_PHRASES[a['reason_code']](a)}"
    text = (f"{head}; usable life {_n(c['usable_life_at_arrival_h'])} h at arrival, "
            f"slack {_n(c['slack_h'])} h, margin ₹{c['margin_inr_kg']:.2f}/kg. "
            f"Dispatch priority #{card['priority']['rank']}.")
    d = card.get("discount")
    if d is not None:
        text += (f" {d['tier_pct']} % off from day {d['day']}: unsold-risk {d['risk']:.2f}"
                 f" -> tier {d['tier_pct']} %")
        text += f", capped by {d['capped_by']}." if d.get("capped_by", "none") != "none" else "."
    return text
