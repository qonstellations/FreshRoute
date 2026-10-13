"""FEFO-greedy and last_day_50 baselines (C-05, ARCHITECTURE.md section 12)."""
import json
from pathlib import Path

import pytest
from validator.validate import validate

from freshroute import cli
from freshroute.io import load_scenario
from freshroute.policies.fefo import FefoPolicy
from freshroute.policies.last_day_50 import LastDay50Policy

ROOT = Path(__file__).parents[1]
SCENARIOS = [ROOT / "tests" / "fixtures" / "tiny_3batch", ROOT / "data" / "scenarios" / "practice"]
DISC_CODES = {"DISCOUNT_CAP", "DISCOUNT_BELOW_SALVAGE", "DISCOUNT_NOT_MONOTONE"}


@pytest.mark.parametrize("path", SCENARIOS, ids=lambda p: p.name)
def test_fefo_has_no_violations(path):
    sc = load_scenario(path)
    res = FefoPolicy().plan(sc)
    assert res.solver is None and res.discounts is None
    assert (res.plan.policy == "fefo").all()
    assert validate(sc, res.plan).violation_total == 0


@pytest.mark.parametrize("path", SCENARIOS, ids=lambda p: p.name)
def test_last_day_50_discounts_are_valid(path):
    sc = load_scenario(path)
    res = LastDay50Policy().plan(sc)
    d = res.discounts
    assert (res.plan.policy == "last_day_50").all() and not d.empty
    assert (d.discount_pct <= 50 + 1e-9).all() and (d.discount_pct >= 0).all()
    codes = {v["code"] for v in validate(sc, res.plan, d).violations}
    assert not codes & DISC_CODES


@pytest.mark.parametrize("policy", ["fefo", "last_day_50"])
def test_cli_run(policy, tmp_path):
    out = cli.run(str(SCENARIOS[0]), policy, 42, str(tmp_path))
    m = json.loads((out / "metrics.json").read_text())
    man = json.loads((out / "run_manifest.json").read_text())
    assert man["solver"] is None
    assert man["flags"]["markdown"] is (policy == "last_day_50")
    assert m["kpis"]["net_inr"] == m["economics_inr"]["net"]
    v = m["volumes_kg"]
    assert abs(v["total_supply"] - v["sold"] - m["kpis"]["spoilage_kg"]
               - v["carryover"]["total"]) < 1e-6
