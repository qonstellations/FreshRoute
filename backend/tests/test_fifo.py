"""FIFO baseline + run pipeline (F-07)."""
import json
from pathlib import Path

from freshroute import cli
from freshroute.io import load_scenario
from freshroute.policies.fifo import FifoPolicy

FIX = Path(__file__).parent / "fixtures" / "tiny_3batch"
FILES = ("plan.csv", "trips.csv", "discounts.csv", "sim_ledger.csv", "sim_lots.csv",
         "metrics.json", "validation.json", "run_manifest.json")


def test_run_writes_outputs_and_reports_violations(tmp_path):
    out = cli.run(str(FIX), "fifo", 42, str(tmp_path))
    assert all((out / f).exists() for f in FILES)
    m = json.loads((out / "metrics.json").read_text())
    # naive FIFO (ARCH 12, A-31) ignores shelf life: violations are reported, not hidden
    assert m["kpis"]["violations"] == 2
    assert json.loads((out / "validation.json").read_text())["counts"] == {"SHELF_LIFE": 2}
    assert m["kpis"]["net_inr"] == m["economics_inr"]["net"]
    v = m["volumes_kg"]
    assert abs(v["total_supply"] - v["sold"] - m["kpis"]["spoilage_kg"]
               - v["carryover"]["total"]) < 1e-6
    assert "net" in cli.format_kpis(m)


def test_deterministic():
    sc = load_scenario(FIX)
    a, b = FifoPolicy().plan(sc), FifoPolicy().plan(sc)
    assert a.plan.equals(b.plan) and a.trips.equals(b.trips)
