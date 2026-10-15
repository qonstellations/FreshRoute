"""discount_advice.json (DATABASE.md section 5.15, A-54)."""
import copy
import json
from pathlib import Path

import pandas as pd

from freshroute import config
from freshroute.cli import run
from freshroute.data.io import load_scenario
from freshroute.domain.discount import COLUMNS
from freshroute.engine.discount_advice import advise
from freshroute.engine.simulator import simulate
from freshroute.policies.fifo import FifoPolicy

SCENARIO = str(Path(__file__).parent / "fixtures" / "tiny_3batch")


def _advice(sc):
    plan = FifoPolicy().plan(sc).plan
    return advise(sc, simulate(sc, plan, pd.DataFrame(columns=list(COLUMNS))))


def test_low_elasticity_never_cuts():
    sc = load_scenario(SCENARIO)
    sc.tables["commodities"]["price_elasticity"] = 0.9
    for a in _advice(sc):
        assert a["best_cut_pct"] == 0.0 and "break-even" in a["reason"]


def test_high_elasticity_cut_respects_caps():
    sc = copy.deepcopy(load_scenario(SCENARIO))
    sc.tables["commodities"]["price_elasticity"] = 50.0
    adv = _advice(sc)
    for a in adv:
        assert 0.0 <= a["best_cut_pct"] <= a["max_cut_pct"] + config.FLOAT_TOL
        assert (a["best_cut_pct"] > 0) == (a["delta_net_inr"] > 0)


def test_run_writes_advice(tmp_path):
    d = run(SCENARIO, "milp", 42, out=str(tmp_path / "r"))
    assert isinstance(json.loads((d / "discount_advice.json").read_text(encoding="utf-8")), list)
