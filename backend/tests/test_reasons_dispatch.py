"""Reason-card text and dispatch-sheet skeleton."""
import re
from pathlib import Path

from freshroute.data.io import load_scenario
from freshroute.engine import dispatch_sheet
from freshroute.engine.reasons import render_text
from freshroute.policies.fifo import FifoPolicy

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
    assert t.startswith("Sent to PUNE, not DELHI: it would reach DELHI with only 9 h of shelf")
    assert "41 h of shelf life left on arrival, 17 h to spare" in t
    assert "priority #3" in t
    assert "20 % off from day 2 (risk of not selling 0.38)" in t


def test_render_text_other_codes_and_no_discount():
    for code in ("WINDOW", "CAPACITY_BOUND", "DEMAND_CAP", "LOWER_MARGIN"):
        card = {**CARD, "discount": None,
                "alternatives": [{**CARD["alternatives"][0], "reason_code": code}]}
        t = render_text(card)
        assert "DELHI" in t and "off from day" not in t
    assert render_text({**CARD, "alternatives": []}).startswith("Sent to PUNE; ")


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
           r"Load: .+ kg \(.+ h to spare\)\nArrive by: day \d+ \d\d:\d\d")
    assert all(re.fullmatch(pat, b) for b in blocks)

    sc.tables["destinations"] = sc.tables["destinations"].drop(columns="name")
    df2, _ = dispatch_sheet.build(sc, r.plan, r.trips)
    assert (df2.dest_name == df2.dest_id).all()


def test_cli_run_writes_dispatch_sheet(tmp_path):
    import pandas as pd

    from freshroute import cli
    out = cli.run(str(FIX), "milp", 42, out=str(tmp_path))
    df = pd.read_csv(out / "dispatch_sheet.csv")
    assert tuple(df.columns) == dispatch_sheet.COLUMNS
    assert len(df) > 0 and df.priority_rank.is_monotonic_increasing
    txt = (out / "dispatch_sheet.txt").read_text(encoding="utf-8")
    assert txt.startswith("Vehicle ")
    assert not re.search(r"\d\.\d\d|day \d+\.\d", txt)  # phone-readable: <= 1 decimal, int days


CODES = {"SHELF_LIFE", "WINDOW", "CAPACITY_BOUND", "DEMAND_CAP", "LOWER_MARGIN"}


def test_build_cards_on_fixture():
    import pandas as pd

    from freshroute.domain.discount import COLUMNS as DISCOUNT_COLUMNS
    from freshroute.engine.reasons import build_cards
    from freshroute.policies.milp import MilpPolicy
    sc = load_scenario(FIX)
    r = MilpPolicy().plan(sc, {"seed": 42})
    none = pd.DataFrame(columns=list(DISCOUNT_COLUMNS))
    cards = build_cards(sc, r.plan, none)
    assert [c["shipment_id"] for c in cards] == sorted(r.plan.shipment_id)
    assert {c["batch_id"] for c in cards} == set(r.plan.batch_id)
    for c in cards:
        assert c["alternatives"] and c["runner_up"]["dest_id"] == c["alternatives"][0]["dest_id"]
        for a in c["alternatives"]:
            assert a["reason_code"] in CODES and a["dest_id"] != c["chosen"]["dest_id"]
            # sign: chosen - alternative; only a capacity/demand-blocked option may beat it
            if a["margin_delta_inr_kg"] < 0:
                assert a["reason_code"] in {"CAPACITY_BOUND", "DEMAND_CAP"}
            if a["reason_code"] == "LOWER_MARGIN":
                assert a["margin_delta_inr_kg"] > 0
        assert c["text"].startswith(f"Sent to {c['chosen']['dest_id']}, not ")
    assert build_cards(sc, r.plan, none) == cards  # deterministic
    assert build_cards(sc, r.plan.iloc[0:0], none) == []


def test_build_cards_scoped_equals_full_and_arcs_override():
    import pandas as pd

    from freshroute.domain.discount import COLUMNS as DISCOUNT_COLUMNS
    from freshroute.domain.feasibility import build_arcs
    from freshroute.engine.reasons import build_cards
    from freshroute.policies.milp import MilpPolicy
    sc = load_scenario(FIX)
    r = MilpPolicy().plan(sc, {"seed": 42})
    none = pd.DataFrame(columns=list(DISCOUNT_COLUMNS))
    scoped = build_cards(sc, r.plan, none)
    full = build_cards(sc, r.plan, none, arcs=build_arcs(sc))
    assert scoped == full
    # pooled-vehicle equivalence: duplicate the fleet, cards must not change
    dup = sc.tables["vehicles"].copy()
    dup["vehicle_id"] = dup["vehicle_id"] + "_DUP"
    sc.tables["vehicles"] = pd.concat([sc.tables["vehicles"], dup], ignore_index=True)
    assert build_cards(sc, r.plan, none) == scoped


def test_cli_run_writes_reason_cards(tmp_path):
    import json

    import pandas as pd

    from freshroute import cli
    out = cli.run(str(FIX), "milp", 42, out=str(tmp_path / "a"))
    first = (out / "reason_cards.json").read_text(encoding="utf-8")
    assert len(json.loads(first)) == len(pd.read_csv(out / "plan.csv"))
    again = cli.run(str(FIX), "milp", 42, out=str(tmp_path / "b"))
    assert (again / "reason_cards.json").read_text(encoding="utf-8") == first


def test_dispatch_sheet_empty_plan():
    sc = load_scenario(FIX)
    r = FifoPolicy().plan(sc)
    df, text = dispatch_sheet.build(sc, r.plan.iloc[0:0], r.trips.iloc[0:0])
    assert df.empty and tuple(df.columns) == dispatch_sheet.COLUMNS and text == ""
