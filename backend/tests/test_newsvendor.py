"""newsvendor demand target (ARCHITECTURE.md section 14.3), --newsvendor, ablation row."""
import json
from pathlib import Path

import pandas as pd
import pytest

from freshroute import cli, newsvendor
from freshroute.config import FLOAT_TOL, NEWSVENDOR_CLAMP
from freshroute.io import load_scenario
from freshroute.policies.milp import MilpPolicy
from freshroute.runs import ladder

ROOT = Path(__file__).parents[2]
TINY = str(ROOT / "backend" / "tests" / "fixtures" / "tiny_3batch")
PRACTICE = str(ROOT / "data" / "scenarios" / "practice")


def _load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def test_quantile_knots_and_tails():
    assert newsvendor.quantile(0.1, 10, 20, 40) == pytest.approx(10)
    assert newsvendor.quantile(0.5, 10, 20, 40) == pytest.approx(20)
    assert newsvendor.quantile(0.9, 10, 20, 40) == pytest.approx(40)
    assert newsvendor.quantile(0.7, 10, 20, 40) == pytest.approx(30)
    assert newsvendor.quantile(0.95, 10, 20, 40) == pytest.approx(42.5)  # end-segment slope
    assert newsvendor.quantile(0.0, 1, 20, 40) == 0.0  # clipped at 0


@pytest.mark.parametrize("scenario", [TINY, PRACTICE])
def test_target_within_p10_p90(scenario):
    sc = load_scenario(scenario)
    t = newsvendor.demand_target(sc)
    d = sc.tables["demand"].merge(t, on=["dest_id", "commodity", "day"])
    assert len(d) == len(sc.tables["demand"]) and list(t.columns) == list(newsvendor.COLUMNS)
    assert (d.target_kg >= d.demand_kg_p10 - FLOAT_TOL).all()
    assert (d.target_kg <= d.demand_kg_p90 + FLOAT_TOL).all()
    assert t.quantile_used.between(*NEWSVENDOR_CLAMP).all()
    off = sc.tables["demand"].merge(newsvendor.demand_target(sc, on=False))
    assert (off.target_kg == off.demand_kg_p50).all()


def test_flag_off_override_is_identity():
    """Off-target == p50, so feeding it through the hook reproduces the default MILP plan."""
    sc = load_scenario(TINY)
    base = MilpPolicy().plan(sc, {"seed": 42}).plan
    ov = newsvendor.override(newsvendor.demand_target(sc, on=False))
    same = MilpPolicy().plan(sc, {"seed": 42, "demand_cap_override": ov}).plan
    pd.testing.assert_frame_equal(base, same)


def test_flag_off_run_unchanged(tmp_path):
    out = cli.run(TINY, "milp_markdown", 42, str(tmp_path / "off"))
    man = _load(out / "run_manifest.json")
    assert man["run_id"] == "tiny_3batch__milp_markdown__s42"
    assert man["flags"]["newsvendor"] is False
    assert not (out / "demand_target.csv").exists()


@pytest.fixture(scope="module")
def nv_runs(tmp_path_factory):
    root = tmp_path_factory.mktemp("nv")
    return [cli.run(TINY, "milp_markdown", 42, str(root / f"r{i}"), newsvendor=True)
            for i in range(2)]


def test_newsvendor_run_valid_and_deterministic(nv_runs):
    a, b = nv_runs
    man = _load(a / "run_manifest.json")
    assert man["run_id"] == "tiny_3batch__milp_markdown__s42__nv"
    assert man["flags"] == {"markdown": True, "newsvendor": True}
    assert _load(a / "validation.json")["violation_total"] == 0
    assert _load(a / "metrics.json")["kpis"]["violations"] == 0
    assert (a / "metrics.json").read_bytes() == (b / "metrics.json").read_bytes()
    assert (a / "demand_target.csv").read_bytes() == (b / "demand_target.csv").read_bytes()


def test_newsvendor_needs_milp(tmp_path):
    with pytest.raises(SystemExit):
        cli.run(TINY, "fefo", 42, str(tmp_path), newsvendor=True)


def test_ladder_ablation_row(tmp_path):
    lad = _load(ladder.run_ladder(TINY, 42, str(tmp_path), newsvendor=True) / "ladder.json")
    (row,) = lad["ablation"]
    plan = next(e["kpis"] for e in lad["ladder"] if e["policy"] == ladder.PLAN)
    assert row["run_id"].endswith("__nv") and row["vs"] == ladder.PLAN
    assert row["delta"]["net_inr"] == pytest.approx(row["kpis"]["net_inr"] - plan["net_inr"])
    nv = _load(tmp_path / row["run_id"] / "metrics.json")["kpis"]  # scored by the one simulator
    assert nv == row["kpis"]
