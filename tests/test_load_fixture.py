"""Placeholder: the tiny_3batch fixture loads and *_pct converts to fractions (S-03)."""
import json
from pathlib import Path

from freshroute import cli
from freshroute.io import load_scenario

FIX = Path(__file__).parent / "fixtures" / "tiny_3batch"


def test_fixture_loads():
    sc = load_scenario(FIX)
    assert len(sc.tables["batches"]) == 3
    assert len(sc.tables["destinations"]) == 2
    assert len(sc.tables["vehicles"]) == 1
    tomato = sc.tables["commodities"].set_index("commodity").loc["tomato"]
    assert abs(tomato["handling_loss_frac"] - 0.025) < 1e-9
    assert "handling_loss_pct" not in sc.tables["commodities"].columns


def test_run_stub_writes_metrics(tmp_path):
    out = cli.run(str(FIX), "milp", 42, str(tmp_path))
    assert json.loads((out / "metrics.json").read_text())["schema_version"] == 1
