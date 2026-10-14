"""Event-driven replan (ARCHITECTURE.md 14.2, DATABASE.md 5.13) on tiny_3batch."""
import json
from pathlib import Path

import pandas as pd
import pytest

from freshroute.cli import main, run
from freshroute.narrator import template_narration
from freshroute.replan import DECISION_COLUMNS, replan_run
from test_narrator import _guard

FIX = Path(__file__).parent / "fixtures"
TINY = str(FIX / "tiny_3batch")
FILES = ("event.json", "plan.csv", "trips.csv", "discounts.csv", "metrics.json",
         "validation.json", "diff.json")
EVENTS = {
    "route_delay": {"target": "HUB1|D2|*", "magnitude": 6},
    "capacity_drop": {"target": "vehicle:V1", "magnitude": 0.8},  # 2000 -> 400 kg
    "demand_spike": {"target": "dest:D1|tomato", "magnitude": 1.5},
    "new_order": {"target": "dest:D2|tomato", "magnitude": 300},
    "price_shock": {"target": "dest:D1|*", "magnitude": 0.8},
}


@pytest.fixture(scope="module")
def base(tmp_path_factory) -> Path:
    return run(TINY, "milp_markdown", 42, str(tmp_path_factory.mktemp("run") / "r"))


def _event(tmp: Path, eid: str, typ: str, at_h: float, **kw) -> Path:
    f = tmp / f"{eid}.json"
    f.write_text(json.dumps({"event_id": eid, "type": typ, "at_h": at_h, **EVENTS[typ], **kw}),
                 encoding="utf-8")
    return f


def _read(d: Path, name: str):
    return json.loads((d / name).read_text(encoding="utf-8"))


def _assert_frozen_unchanged(old: pd.DataFrame, new: pd.DataFrame, at_h: float, timing=True):
    frozen = new[new.is_frozen]
    assert len(frozen) == ((old.dispatch_h <= at_h) | old.is_frozen).sum()
    cols = list(DECISION_COLUMNS) + ([] if not timing else
                                     ["arrival_h", "arrival_day", "usable_life_at_arrival_h"])
    o = old.set_index("shipment_id").loc[frozen.shipment_id].reset_index()
    pd.testing.assert_frame_equal(frozen[cols].reset_index(drop=True), o[cols],
                                  check_dtype=False)
    assert (new[~new.is_frozen].dispatch_h >= at_h).all()


@pytest.mark.parametrize("typ", sorted(EVENTS))
def test_replan_each_event_type(base, tmp_path, typ):
    out = replan_run(base, _event(tmp_path, f"E-{typ}", typ, 8.0), tmp_path / "out")
    assert all((out / f).exists() for f in FILES)
    v, m, d = _read(out, "validation.json"), _read(out, "metrics.json"), _read(out, "diff.json")
    assert v["violation_total"] == 0 and m["kpis"]["violations"] == 0
    assert d["kpis_replanned"] == {k: m["kpis"][k] for k in d["kpis_replanned"]}
    for k, x in d["delta_kpis"].items():  # deltas are simulator KPIs, replanned - old
        assert x == pytest.approx(d["kpis_replanned"][k] - d["kpis_old_plan_under_event"][k])
    fixture = json.loads((FIX / "diff_example.json").read_text(encoding="utf-8"))
    assert set(fixture) - {"_note"} <= set(d)  # the frontend fixture is a real subset
    old, new = pd.read_csv(base / "plan.csv"), pd.read_csv(out / "plan.csv")
    _assert_frozen_unchanged(old, new, 8.0, timing=typ != "route_delay")
    assert d["frozen_shipments"] == int(new.is_frozen.sum()) > 0
    assert new.shipment_id.is_unique
    trips = pd.read_csv(out / "trips.csv")
    assert trips.trip_id.is_unique and set(trips.trip_id) == set(new.trip_id)


def test_route_delay_retimes_frozen_in_transit(base, tmp_path):
    out = replan_run(base, _event(tmp_path, "E1", "route_delay", 8.0), tmp_path / "o")
    new = pd.read_csv(out / "plan.csv")
    old = pd.read_csv(base / "plan.csv").set_index("shipment_id")
    f = new[new.is_frozen & (new.dest_id == "D2")]
    assert len(f) and (f.arrival_h.values == old.loc[f.shipment_id].arrival_h.values + 6).all()
    g = new[new.is_frozen & (new.dest_id == "D1")]  # other lanes untouched
    assert (g.arrival_h.values == old.loc[g.shipment_id].arrival_h.values).all()


def test_capacity_drop_old_plan_violates_replan_does_not(base, tmp_path):
    out = replan_run(base, _event(tmp_path, "E1", "capacity_drop", 8.0), tmp_path / "o")
    d, v = _read(out, "diff.json"), _read(out, "validation.json")
    assert d["kpis_old_plan_under_event"]["violations"] > 0  # undispatched trips now too big
    assert d["kpis_replanned"]["violations"] == 0 == v["violation_total"]
    # frozen day-0 trips left loaded above the new capacity: shown, not counted (A-43)
    assert {w["code"] for w in v["warnings"]} >= {"FROZEN_VEHICLE_CAPACITY"}
    trips = pd.read_csv(out / "trips.csv")
    new = trips[~trips.trip_id.isin(pd.read_csv(base / "trips.csv").trip_id)]
    assert (new.kg_total <= 400 + 1e-6).all()


def test_event_before_first_dispatch(base, tmp_path):
    out = replan_run(base, _event(tmp_path, "E0", "price_shock", 0.0, magnitude=1.0),
                     tmp_path / "o")
    d, new = _read(out, "diff.json"), pd.read_csv(out / "plan.csv")
    assert d["frozen_shipments"] == 0 and not new.is_frozen.any()
    assert _read(out, "validation.json")["violation_total"] == 0
    # a no-op event re-solves from the old plan; within the 1 % MIP gap the plan may still
    # change (measured -285 INR on tiny), so only the old side is pinned
    assert d["kpis_old_plan_under_event"] == pytest.approx({
        k: _read(base, "metrics.json")["kpis"][k] for k in d["kpis_old_plan_under_event"]})


def test_event_after_everything_dispatched(base, tmp_path):
    out = replan_run(base, _event(tmp_path, "E9", "demand_spike", 1000.0), tmp_path / "o")
    d = _read(out, "diff.json")
    old, new = pd.read_csv(base / "plan.csv"), pd.read_csv(out / "plan.csv")
    assert d["frozen_shipments"] == len(old) == len(new) and new.is_frozen.all()
    assert d["moved_batches"] == []
    assert all(x == pytest.approx(0) for x in d["delta_kpis"].values())
    _assert_frozen_unchanged(old, new, 1000.0)
    assert _read(out, "validation.json")["violation_total"] == 0


def test_two_events_in_a_row(base, tmp_path):
    first = replan_run(base, _event(tmp_path, "E1", "capacity_drop", 8.0))
    assert first == base / "replan" / "E1"
    second = replan_run(first, _event(tmp_path, "E2", "demand_spike", 30.0))
    assert second == first / "replan" / "E2"
    p1, p2 = pd.read_csv(first / "plan.csv"), pd.read_csv(second / "plan.csv")
    _assert_frozen_unchanged(p1, p2, 30.0)
    assert set(p1[p1.is_frozen].shipment_id) < set(p2[p2.is_frozen].shipment_id)
    assert _read(second, "validation.json")["violation_total"] == 0
    # the second replan sees both events: V1 capacity stays dropped
    trips = pd.read_csv(second / "trips.csv")
    late = trips[~trips.trip_id.isin(pd.read_csv(first / "trips.csv").trip_id)]
    assert (late.kg_total <= 400 + 1e-6).all()


def test_deterministic(base, tmp_path):
    ev = _event(tmp_path, "E1", "new_order", 8.0)
    a, b = replan_run(base, ev, tmp_path / "a"), replan_run(base, ev, tmp_path / "b")
    da, db = _read(a, "diff.json"), _read(b, "diff.json")
    da.pop("solve_seconds"), db.pop("solve_seconds")  # the only field allowed to differ
    assert da == db
    for f in ("plan.csv", "trips.csv", "discounts.csv", "metrics.json", "validation.json"):
        assert (a / f).read_bytes() == (b / f).read_bytes(), f


def test_narration_over_real_diff(base, tmp_path):
    out = replan_run(base, _event(tmp_path, "E1", "capacity_drop", 8.0), tmp_path / "o")
    d, m = _read(out, "diff.json"), _read(out, "metrics.json")
    text = template_narration(d, m)
    assert text.startswith("Event E1 at hour 8:")
    _guard(text, d, m, extra=[len(d["moved_batches"]), len(d["discount_changes"]), 1, 3])


def test_cli_replan(base, tmp_path, capsys):
    main(["replan", "--run", str(base), "--event",
          str(_event(tmp_path, "E7", "price_shock", 8.0)), "--out", str(tmp_path / "c")])
    assert "0 violation(s)" in capsys.readouterr().out
    assert (tmp_path / "c" / "diff.json").exists()


def test_cli_replan_creates_missing_run(tmp_path, capsys):
    run_dir = tmp_path / "fresh"
    main(["replan", "--run", str(run_dir), "--scenario", TINY, "--policy", "milp", "--event",
          str(_event(tmp_path, "E8", "new_order", 8.0))])
    assert (run_dir / "plan.csv").exists() and (run_dir / "replan" / "E8" / "diff.json").exists()
