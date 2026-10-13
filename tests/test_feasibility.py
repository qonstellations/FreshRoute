"""One test per reject reason, both window modes, determinism (F-02)."""
from pathlib import Path

import pandas as pd
import pytest

from freshroute.config import FLOAT_TOL
from freshroute.feasibility import REASONS, build_arcs
from freshroute.io import load_scenario

ROOT = Path(__file__).parent
FIX = ROOT / "fixtures" / "tiny_3batch"
PRACTICE = ROOT.parent / "data" / "scenarios" / "practice"


def sc():
    return load_scenario(FIX)


def arc(df, b="B1", d="D1", v="V1", day=0):
    m = df[(df.batch_id == b) & (df.dest_id == d) & (df.vehicle_id == v) & (df.dispatch_day == day)]
    assert len(m) == 1
    return m.iloc[0]


def test_baseline_feasible_and_worked_numbers():
    df = build_arcs(sc())
    assert len(df) == 3 * 2 * 1 * 3
    a = arc(df)  # B1 -> D1 day 0: dispatch 5, travel 12 (10 C reefer, decay .5), handling 2
    assert a.feasible and a.reject_reason == ""
    assert a.usable_life_at_arrival_h == pytest.approx(100 - 5 - 6 - 2, abs=FLOAT_TOL)
    assert a.slack_h == pytest.approx(87 - 24, abs=FLOAT_TOL)
    assert a.arrival_h == pytest.approx(17)
    assert a.margin_inr_kg == pytest.approx(30 * (1 - 0.025) - 2.0 - 1.0)


def test_no_lane():
    s = sc()
    s.tables["lanes"] = s.tables["lanes"][s.tables["lanes"].dest_id != "D2"]
    df = build_arcs(s)
    assert arc(df, d="D2").reject_reason == "NO_LANE"
    assert arc(df, d="D1").feasible


def test_not_available():
    s = sc()
    s.tables["batches"].loc[s.tables["batches"].batch_id == "B2", "available_from_h"] = 30
    df = build_arcs(s)
    assert arc(df, b="B2", day=0).reject_reason == "NOT_AVAILABLE"
    assert arc(df, b="B2", day=1).dispatch_h == pytest.approx(30)  # waits for availability


def test_not_available_zero_trips():
    s = sc()
    s.tables["vehicles"]["max_trips_day"] = 0
    assert (build_arcs(s).reject_reason == "NOT_AVAILABLE").all()


def _rail(s, slots):
    s.tables["lanes"]["mode"] = "rail"
    s.tables["lanes"]["departure_slots"] = slots
    s.tables["vehicles"]["mode"] = "rail"
    return s


def test_rail_slot_moves_dispatch():
    a = arc(build_arcs(_rail(sc(), "18|22")))
    assert a.dispatch_h == pytest.approx(18)


def test_rail_slot_rejected_when_slot_leaves_day():
    df = build_arcs(_rail(sc(), "3"))  # day-0 05:00 -> next slot is 03:00 of day 1
    assert arc(df, day=0).reject_reason == "RAIL_SLOT"


def test_window_absolute():
    s = sc()
    s.tables["destinations"]["window_close_h"] = 20
    df = build_arcs(s)
    assert arc(df, day=0).feasible  # arrival 17
    assert arc(df, day=1).reject_reason == "WINDOW"  # arrival 41


def test_window_daily():
    s = sc()
    s.meta["window_mode"] = "daily"
    s.tables["destinations"]["window_open_h"] = 6
    s.tables["destinations"]["window_close_h"] = 20
    assert all(arc(build_arcs(s), day=k).feasible for k in range(3))  # hour-of-day 17 each day
    s.tables["destinations"]["window_open_h"] = 18
    assert arc(build_arcs(s), day=1).reject_reason == "WINDOW"
    s.tables["destinations"]["window_open_h"] = 0
    s.tables["destinations"]["window_close_h"] = 12
    assert arc(build_arcs(s), day=1).reject_reason == "WINDOW"
    s.meta["window_mode"] = "absolute"  # absolute 0..12: arrival 41 -> still window, day 0 17 too
    s.tables["destinations"]["window_close_h"] = 48
    assert arc(build_arcs(s), day=1).feasible


def test_shelf_life():
    df = build_arcs(sc())
    # B2 RSL 60 -> D2 day0: 60-5-9-2 = 44 ok; day 1 waits 29 h: 60-29-9-2 = 20 < 24
    assert arc(df, b="B2", d="D2", day=0).feasible
    a = arc(df, b="B2", d="D2", day=1)
    assert a.reject_reason == "SHELF_LIFE"
    assert a.slack_h < 0


def test_beyond_horizon():
    s = sc()
    s.tables["destinations"]["window_close_h"] = 1000
    s.tables["lanes"]["travel_h_p50"] = 40.0
    s.tables["lanes"]["travel_h_p90"] = 40.0
    s.tables["batches"]["remaining_shelf_life_h"] = 1000.0
    s.tables["batches"]["rsl_p90_h"] = 1000.0
    df = build_arcs(s)
    a = arc(df, day=2)  # dispatch 53 h + 40 = 93 h -> day 3 > horizon - 1
    assert a.reject_reason == "BEYOND_HORIZON"
    assert a.arrival_day == 3
    assert arc(df, day=1).feasible


def test_reasons_are_known():
    assert set(build_arcs(sc()).reject_reason) - {""} <= set(REASONS)


def test_realization_override():
    assert arc(build_arcs(sc(), {"rsl_h": {"B1": 20}})).reject_reason == "SHELF_LIFE"


def test_deterministic():
    pd.testing.assert_frame_equal(build_arcs(sc()), build_arcs(sc()))


@pytest.mark.skipif(not PRACTICE.exists(), reason="practice scenario not generated")
def test_practice_has_feasible_and_rejected():
    df = build_arcs(load_scenario(PRACTICE))
    assert df.feasible.any()
    assert (~df.feasible).any()
