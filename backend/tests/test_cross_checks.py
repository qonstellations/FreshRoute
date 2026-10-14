"""Cross-checks: expected fixture vs simulate+metrics (A); validator vs shelflife maths (B)."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from freshroute.io import load_scenario
from freshroute.metrics import compute
from freshroute.shelflife import usable_life_at_arrival
from freshroute.simulator import simulate
from validator.rules import usable_life

FIX = Path(__file__).parent / "fixtures" / "tiny_3batch"


def _flat(d, p=""):
    for k, v in d.items():
        if isinstance(v, dict):
            yield from _flat(v, f"{p}{k}.")
        elif isinstance(v, (int, float)) and not isinstance(v, bool):
            yield p + k, v


def test_expected_fixture_matches_pipeline():
    sc = load_scenario(FIX)
    exp = FIX / "expected"
    plan, trips = pd.read_csv(exp / "plan.csv"), pd.read_csv(exp / "trips.csv")
    disc = pd.read_csv(exp / "discounts.csv")
    got = compute(sc, plan, disc, simulate(sc, plan, disc))
    want = json.loads((exp / "metrics.json").read_text())
    assert len(trips) == got["trips"]["count"]
    g = dict(_flat(got))
    for k, v in _flat(want):
        assert g[k] == pytest.approx(v, abs=1e-6), k


def test_usable_life_agrees_with_shelflife():
    rng = np.random.default_rng(7)
    for _ in range(200):
        a = (rng.uniform(0, 500), rng.uniform(0, 48), rng.uniform(0, 48), rng.uniform(0, 6),
             rng.uniform(0, 30), rng.uniform(0, 30), rng.uniform(5, 25), rng.uniform(1.2, 3.5))
        assert usable_life(*a) == pytest.approx(usable_life_at_arrival(*a), rel=1e-9, abs=1e-9)
