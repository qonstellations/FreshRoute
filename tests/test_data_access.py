import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
import data_access  # noqa: E402


def test_fixture_fallback_has_tile_fields(tmp_path):
    assert data_access.list_runs(tmp_path) == []
    m, is_fixture = data_access.load_metrics(outputs=tmp_path)
    assert is_fixture
    for f in ("spoilage_kg", "spoilage_pct", "demand_fulfillment_pct", "net_inr", "violations"):
        assert f in m["kpis"]


def test_fixture_invariants(tmp_path):
    m, _ = data_access.load_metrics(outputs=tmp_path)
    e, v, b = m["economics_inr"], m["volumes_kg"], m["spoilage_breakdown_kg"]
    assert e["revenue"] == e["gross_revenue_at_list"] - e["discount_cost"]
    assert e["net"] == e["revenue"] - e["transport"] - e["handling"] - e["spoilage_cost"]
    assert e["net"] == m["kpis"]["net_inr"]
    assert sum(b.values()) == m["kpis"]["spoilage_kg"]
    assert v["total_supply"] == v["sold"] + m["kpis"]["spoilage_kg"] + v["carryover"]["total"]
    assert v["total_supply"] == v["shipped"] + v["unshipped"]


def _write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj), encoding="utf-8")


def test_run_loaders_absent_return_none(tmp_path):
    assert data_access.load_validation("x__milp__s42", tmp_path) is None
    assert data_access.load_manifest("x__milp__s42", tmp_path) is None
    assert data_access.load_validation(None, tmp_path) is None
    assert data_access.load_ladder("x", 42, tmp_path) is None
    assert data_access.load_baseline("x", 42, tmp_path) is None


def test_run_loaders_read_files(tmp_path):
    v = {"violation_total": 2, "counts": {"SHELF_LIFE": 2}, "warnings": []}
    _write(tmp_path / "x__milp__s42" / "validation.json", v)
    _write(tmp_path / "x__milp__s42" / "run_manifest.json", {"solver": {"fallback_used": True}})
    assert data_access.load_validation("x__milp__s42", tmp_path) == v
    assert data_access.load_manifest("x__milp__s42", tmp_path)["solver"]["fallback_used"]


def test_baseline_from_sibling_fefo_run(tmp_path):
    _write(tmp_path / "x__fefo__s42" / "metrics.json", {"kpis": {"violations": 3}})
    b = data_access.load_baseline("x", 42, tmp_path)
    assert b == {"policy": "fefo", "kpis": {"violations": 3}, "source": "run"}
    assert data_access.load_baseline("x", 7, tmp_path) is None


def test_baseline_ladder_preferred_and_fefo_when_official_null(tmp_path):
    _write(tmp_path / "x__fefo__s42" / "metrics.json", {"kpis": {"violations": 3}})
    lad = {"official_baseline": None,
           "ladder": [{"policy": "fifo", "kpis": {"violations": 9}},
                      {"policy": "fefo", "kpis": {"violations": 1}}]}
    _write(tmp_path / "x__ladder__s42" / "ladder.json", lad)
    b = data_access.load_baseline("x", 42, tmp_path)
    assert (b["policy"], b["kpis"], b["source"]) == ("fefo", {"violations": 1}, "ladder")
    lad["official_baseline"] = {"policy": "organizer_baseline", "kpis": {"violations": 5}}
    _write(tmp_path / "x__ladder__s42" / "ladder.json", lad)
    assert data_access.load_baseline("x", 42, tmp_path)["policy"] == "organizer_baseline"


def test_app_script_runs_without_exceptions():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py"))
    at.run(timeout=30)
    assert not at.exception
    assert any("SYNTHETIC DATA" in w.value for w in at.warning)
