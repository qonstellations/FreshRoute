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
