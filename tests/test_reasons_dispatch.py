"""Reason-card text and dispatch-sheet skeleton (C-13)."""
import re
from pathlib import Path

from freshroute import dispatch_sheet
from freshroute.io import load_scenario
from freshroute.policies.fifo import FifoPolicy
from freshroute.reasons import render_text

FIX = Path(__file__).parent / "fixtures" / "tiny_3batch"

CARD = {  # DATABASE.md 5.9 example
    "shipment_id": "S0007", "batch_id": "B014", "commodity": "tomato",
    "chosen": {"dest_id": "PUNE", "vehicle_id": "V03", "mode": "reefer", "dispatch_h": 5.0,
               "arrival_h": 17.0, "usable_life_at_arrival_h": 41.0, "slack_h": 17.0,
               "margin_inr_kg": 0.0},
    "priority": {"rank": 3, "score": 0.0},
    "alternatives": [{"dest_id": "DELHI", "mode": "ambient", "dispatch_day": 0, "feasible": False,
                      "reject_reason": "SHELF_LIFE", "usable_life_at_arrival_h": 9.0,
                      "margin_inr_kg": 0.0, "reason_code": "SHELF_LIFE"}],
    "discount": {"day": 2, "risk": 0.38, "tier_pct": 20, "capped_by": "none"},
    "text": "",
}


def test_render_text_example_card():
    t = render_text(CARD)
    assert t.startswith("Sent to PUNE, not DELHI: DELHI arrival leaves 9 h of life")
    assert "usable life 41 h at arrival, slack 17 h" in t
    assert "priority #3" in t
    assert "20 % off from day 2: unsold-risk 0.38" in t


def test_render_text_other_codes_and_no_discount():
    for code in ("WINDOW", "CAPACITY_BOUND", "DEMAND_CAP", "LOWER_MARGIN"):
        card = {**CARD, "discount": None,
                "alternatives": [{**CARD["alternatives"][0], "reason_code": code}]}
        t = render_text(card)
        assert "DELHI" in t and "off from day" not in t
    assert render_text({**CARD, "alternatives": []}).startswith("Sent to PUNE; usable life")


def test_dispatch_sheet_on_fixture():
    sc = load_scenario(FIX)
    r = FifoPolicy().plan(sc)
    df, text = dispatch_sheet.build(sc, r.plan, r.trips)
    assert tuple(df.columns) == dispatch_sheet.COLUMNS
    assert len(df) == len(r.plan)
    assert df.priority_rank.is_monotonic_increasing
    assert df.depart_clock.str.fullmatch(r"\d\d:\d\d").all()
    assert set(df.dest_name) <= {"Mandi One", "Retail DC Two"}
    assert set(df.commodity) <= {"tomato", "onion"}
    blocks = text.strip().split("\n\n")
    assert len(blocks) == r.trips.trip_id.nunique()
    pat = (r"Vehicle \S+ \| Trip \S+ \| Depart \d\d:\d\d \(day \d+\)\nTo: .+\n"
           r"Load: .+ kg \(slack .+ h\)\nArrive by: day \d+ \d\d:\d\d")
    assert all(re.fullmatch(pat, b) for b in blocks)

    sc.tables["destinations"] = sc.tables["destinations"].drop(columns="name")
    df2, _ = dispatch_sheet.build(sc, r.plan, r.trips)
    assert (df2.dest_name == df2.dest_id).all()
