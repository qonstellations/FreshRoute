"""Monte Carlo stress test (ARCHITECTURE.md 14.1, DATABASE.md 5.12) on tiny_3batch."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from freshroute import config, stress
from freshroute.cli import main
from freshroute.io import load_scenario
from freshroute.simulator import simulate

FIX = Path(__file__).parent / "fixtures"
SCENARIO = str(FIX / "tiny_3batch")


def _run(tmp_path, name, *extra):
    main(["stress", "--scenario", SCENARIO, "--n", "12", "--seed", "42",
          "--out", str(tmp_path / name), *extra])
    return tmp_path / name


def test_deterministic_schema_and_bands(tmp_path):
    a, b = _run(tmp_path, "a"), _run(tmp_path, "b")
    for f in ("stress.csv", "stress_summary.json"):
        assert (a / f).read_bytes() == (b / f).read_bytes()
    s = json.loads((a / "stress_summary.json").read_text(encoding="utf-8"))
    ex = json.loads((FIX / "stress_summary_example.json").read_text(encoding="utf-8"))
    ex.pop("_note")
    assert s.keys() == ex.keys() and s["bands"].keys() == ex["bands"].keys()
    assert s["share_plan_beats_baseline"].keys() == ex["share_plan_beats_baseline"].keys()
    assert s["n"] == 12 and (s["plan"], s["baseline"]) == ("milp_markdown", "fefo")
    for kpi in s["bands"].values():
        for band in kpi.values():
            assert band.keys() == {"p10", "p50", "p90"}
            assert band["p10"] <= band["p50"] <= band["p90"]
    assert all(0.0 <= v <= 1.0 for v in s["share_plan_beats_baseline"].values())
    df = pd.read_csv(a / "stress.csv")
    assert list(df.columns) == list(stress.COLUMNS) and len(df) == 24
    assert (df.groupby("scenario_i").policy.nunique() == 2).all()


def test_draws_paired_and_seeded():
    sc = load_scenario(SCENARIO)
    d1, d2 = stress.draws(sc, 3, 42), stress.draws(sc, 3, 42)
    for x, y in zip(d1, d2, strict=True):
        assert all(np.array_equal(p, q) for p, q in zip(x, y, strict=True))
    # scenario i depends only on base_seed + i, not on n
    one = stress.draws(sc, 1, 43)[0]
    assert all(np.array_equal(p, q) for p, q in zip(one, d1[1], strict=True))
    assert len(stress.draws(sc, 99, 42, named=True)) == len(config.MC_NAMED)


def test_named_fallback(tmp_path):
    s = json.loads((_run(tmp_path, "n", "--named") / "stress_summary.json").read_text("utf-8"))
    assert s["n"] == len(config.MC_NAMED)


def test_pairing_both_policies_see_same_realization(monkeypatch, tmp_path):
    seen = []
    real_sim = stress.simulate
    monkeypatch.setattr(stress, "simulate",
                        lambda sc, p, d, r: seen.append(r) or real_sim(sc, p, d, r))
    _run(tmp_path, "p")
    assert len(seen) == 24
    assert all(seen[2 * i] is seen[2 * i + 1] for i in range(12))
    assert seen[0] != seen[2]


def test_p50_realization_reproduces_base():
    """Sampling at u = 0.5 everywhere is the base realization: the stressed simulator path
    (re-timed lots, sampled RSL) must give the base metrics."""
    sc = load_scenario(SCENARIO)
    plan, disc = stress._solve(sc, "milp_markdown", 42)
    real = stress.realization(sc, *stress.draws(sc, 1, 42, named=True)[1])
    a, b = simulate(sc, plan, disc), simulate(sc, plan, disc, real)
    pd.testing.assert_frame_equal(a["ledger"], b["ledger"], check_exact=False, atol=1e-9)
    pd.testing.assert_frame_equal(a["origin"], b["origin"], check_exact=False, atol=1e-9)


def test_inverse_cdf_shape():
    assert np.allclose(stress.inv_cdf([0.1, 0.5, 0.9], 10, 20, 50), [10, 20, 50])
    assert stress.inv_cdf(0.0, 10, 20, 50) == 7.5  # end-segment slope
    assert stress.inv_cdf(0.0, 1, 20, 50) == 0.0  # clipped at 0
    t = stress.travel_draw([0.2, 0.5, 0.7, 1.0], 10, 14)
    assert np.allclose(t, [10, 10, 12, min(10 + 0.5 * 10, 1.5 * 14)])
