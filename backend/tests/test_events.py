"""Event schema and application (DATABASE.md section 6)."""
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from freshroute.data.events import Event, EventError, apply_event, load_event
from freshroute.data.io import load_scenario

FIX = Path(__file__).parent / "fixtures"
TINY = FIX / "tiny_3batch"

GOOD = [
    {"event_id": "E1", "type": "route_delay", "target": "HUB1|D2|*", "magnitude": 6, "at_h": 8,
     "note": "NH-48 jam"},
    {"event_id": "E2", "type": "capacity_drop", "target": "vehicle:V1", "magnitude": 0.5,
     "at_h": 8},
    {"event_id": "E3", "type": "capacity_drop", "target": "dest:D1", "magnitude": 1, "at_h": 0},
    {"event_id": "E4", "type": "demand_spike", "target": "dest:D1|*", "magnitude": 1.5,
     "at_h": 30},
    {"event_id": "E5", "type": "new_order", "target": "dest:D2|tomato", "magnitude": 300,
     "at_h": 30},
    {"event_id": "E6", "type": "price_shock", "target": "dest:D1|onion", "magnitude": 0.8,
     "at_h": 8},
]
BAD = [
    {"type": "flood"},  # unknown type
    {"type": "route_delay", "target": "HUB1|D2"},  # wrong arity
    {"type": "route_delay", "magnitude": -1},
    {"type": "capacity_drop", "target": "truck:V1"},
    {"type": "capacity_drop", "magnitude": 1.5},
    {"type": "demand_spike", "target": "D1|tomato"},  # missing dest: prefix
    {"type": "demand_spike", "magnitude": 0},
    {"type": "new_order", "target": "dest:D2|*"},  # no wildcard for new_order
    {"type": "new_order", "magnitude": -5},
    {"type": "price_shock", "target": "dest:*|tomato"},
    {"at_h": -1},
    {"surprise": 1},  # unknown field
    {"magnitude": float("nan")},
]


@pytest.mark.parametrize("ev", GOOD, ids=[e["type"] + e["event_id"] for e in GOOD])
def test_good_events_validate(ev):
    e = Event.model_validate(ev)
    assert e.at_h == float(ev["at_h"]) and e.magnitude == float(ev["magnitude"])


@pytest.mark.parametrize("patch", BAD, ids=[str(i) for i in range(len(BAD))])
def test_bad_events_rejected(patch):
    base = {"route_delay": GOOD[0], "capacity_drop": GOOD[1], "demand_spike": GOOD[3],
            "new_order": GOOD[4], "price_shock": GOOD[5]}.get(patch.get("type"), GOOD[0])
    with pytest.raises(ValidationError):
        Event.model_validate({**base, **patch})


@pytest.mark.parametrize("target", ["vehicle:V9", "dest:D9"])
def test_unknown_capacity_target_rejected(target):
    sc = load_scenario(TINY)
    with pytest.raises(EventError):
        apply_event(sc, Event.model_validate({**GOOD[1], "target": target}))


@pytest.mark.parametrize("target", ["dest:D9|tomato", "dest:D1|kiwi"])
def test_unknown_dest_or_commodity_rejected(target):
    sc = load_scenario(TINY)
    with pytest.raises(EventError):
        apply_event(sc, Event.model_validate({**GOOD[5], "target": target}))


def test_unknown_lane_rejected():
    sc = load_scenario(TINY)
    with pytest.raises(EventError):
        apply_event(sc, Event.model_validate({**GOOD[0], "target": "HUB9|*|*"}))


def test_apply_effects_and_original_untouched():
    sc = load_scenario(TINY)
    before = {k: v.copy() for k, v in sc.tables.items()}
    ev = [Event.model_validate(e) for e in GOOD]
    ln = apply_event(sc, ev[0]).tables["lanes"].set_index("dest_id")
    assert ln.travel_h_p50["D2"] == 24 and ln.travel_h_p90["D2"] == 30
    assert ln.travel_h_p50["D1"] == 12
    assert apply_event(sc, ev[1]).tables["vehicles"].capacity_kg.iloc[0] == 1000
    dst = apply_event(sc, ev[2]).tables["destinations"].set_index("dest_id")
    assert dst.receive_cap_kg_day["D1"] == 0 and dst.receive_cap_kg_day["D2"] == 1500
    dem = apply_event(sc, ev[3]).tables["demand"].set_index(["dest_id", "commodity", "day"])
    assert dem.demand_kg_p50[("D1", "tomato", 0)] == 400  # day 0 < day(at_h = 30) = 1
    assert dem.demand_kg_p50[("D1", "tomato", 1)] == 600
    assert dem.demand_kg_p90[("D1", "onion", 2)] == 600
    dem = apply_event(sc, ev[4]).tables["demand"].set_index(["dest_id", "commodity", "day"])
    old = before["demand"].set_index(["dest_id", "commodity", "day"])
    assert dem.demand_kg_p50[("D2", "tomato", 1)] == old.demand_kg_p50[("D2", "tomato", 1)] + 300
    assert dem.demand_kg_p50[("D2", "tomato", 0)] == old.demand_kg_p50[("D2", "tomato", 0)]
    pr = apply_event(sc, ev[5]).tables["prices"].set_index(["dest_id", "commodity", "day"])
    op = before["prices"].set_index(["dest_id", "commodity", "day"])
    assert pr.price_inr_kg[("D1", "onion", 0)] == pytest.approx(0.8 * op.price_inr_kg[
        ("D1", "onion", 0)])
    for k, v in before.items():  # apply_event never mutates its input
        assert v.equals(sc.tables[k]), k


def test_load_event_roundtrip(tmp_path):
    f = tmp_path / "e.json"
    f.write_text(json.dumps(GOOD[0]), encoding="utf-8")
    assert load_event(f) == Event.model_validate(GOOD[0])


def test_diff_example_refers_to_a_valid_event():
    d = json.loads((FIX / "diff_example.json").read_text(encoding="utf-8"))
    Event(event_id=d["event_id"], type="route_delay", target="*|D2|*", magnitude=6,
          at_h=d["at_h"])
    assert all(lot["lot_id"].count("@") == 2 and lot["lot_id"].rsplit("@", 1)[1].isdigit()
               for lot in d["discount_changes"])  # lot_id day is an int (discount.lots)
