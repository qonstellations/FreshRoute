"""MILP skeleton on tiny_3batch (F-03): supply, capacity, demand, fallback, determinism."""
from pathlib import Path

import pandas as pd

from freshroute import config
from freshroute.io import load_scenario
from freshroute.policies import milp
from freshroute.policies.milp import MilpPolicy

FIX = Path(__file__).parent / "fixtures" / "tiny_3batch"
TOL = config.FLOAT_TOL


def sc():
    return load_scenario(FIX)


def check_valid(plan, s):
    t = s.tables
    p, tr = plan.plan, plan.trips
    assert len(p) > 0
    sup = t["batches"].set_index("batch_id").qty_kg
    shipped = p.groupby("batch_id").kg.sum()
    assert (shipped <= sup.reindex(shipped.index) + TOL).all()
    assert (tr.kg_total <= tr.capacity_kg + TOL).all()
    assert abs(p.kg.sum() - tr.kg_total.sum()) < TOL
    assert set(p.trip_id) <= set(tr.trip_id)
    cap = t["destinations"].set_index("dest_id").receive_cap_kg_day
    for (d, _), g in p.groupby(["dest_id", "arrival_day"]):
        assert g.kg.sum() <= cap[d] + TOL
    com = t["batches"].set_index("batch_id").commodity
    dem = t["demand"].set_index(["dest_id", "commodity", "day"]).demand_kg_p50
    q = p.assign(c=p.batch_id.map(com)).groupby(["dest_id", "c", "arrival_day"]).kg.sum()
    for (d, c, a), kg in q.items():
        assert kg <= dem.get((d, c, a), 0) * (1 + config.OVERSHIP_SLACK) + TOL
    vmax = t["vehicles"].set_index("vehicle_id").max_trips_day
    for (v, _), g in tr.groupby(["vehicle_id", "dispatch_day"]):
        assert len(g) <= vmax[v]
    return True


def test_solves_tiny():
    s = sc()
    plan = MilpPolicy().plan(s)
    assert check_valid(plan, s)
    assert plan.solver["fallback_used"] is False
    # profitable fixture: demand dominates, most stock should ship
    assert plan.plan.kg.sum() > 1000


def test_tiny_time_limit_never_crashes():
    s = sc()
    plan = MilpPolicy().plan(s, {"time_limit_s": 0.0})
    assert check_valid(plan, s)


def test_greedy_fallback_valid(monkeypatch):
    s = sc()
    monkeypatch.setattr(milp, "_solve", lambda *a, **k: (None, {"status": "forced"}))
    plan = MilpPolicy().plan(s)
    assert plan.solver["fallback_used"] is True
    assert check_valid(plan, s)


def test_deterministic():
    s = sc()
    a, b = MilpPolicy().plan(s), MilpPolicy().plan(s)
    pd.testing.assert_frame_equal(a.plan, b.plan)
    pd.testing.assert_frame_equal(a.trips, b.trips)


def test_fefo_tiebreak_small():
    # section 9.2: eps/usable_life stays under 1 % of the smallest per-kg margin
    for path in (FIX, Path(__file__).parents[1] / "data" / "scenarios" / "practice"):
        arcs, _, _ = milp._model_data(load_scenario(path))
        tie = (config.EPS_FEFO / arcs.usable_life_at_arrival_h).max()
        assert tie < 0.01 * arcs.margin_inr_kg.abs().min(), path
