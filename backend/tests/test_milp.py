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
    for path in (FIX, Path(__file__).parents[2] / "data" / "scenarios" / "practice"):
        arcs, _, _ = milp._model_data(load_scenario(path))
        tie = (config.EPS_FEFO / arcs.usable_life_at_arrival_h).max()
        assert tie < 0.01 * arcs.margin_inr_kg.abs().min(), path


def test_solver_info_and_c6():
    s = sc()
    plan = MilpPolicy().plan(s)
    assert plan.solver["mip_gap"] <= config.MIP_REL_GAP + TOL
    assert isinstance(plan.solver["slack_usage"], dict)
    com = s.tables["batches"].set_index("batch_id").commodity
    arcs, _, _ = milp._model_data(s)
    dem = s.tables["demand"].set_index(["dest_id", "commodity", "day"]).demand_kg_p50
    tot = {}
    for d, c, a in set(zip(arcs.dest_id, arcs.commodity, arcs.arrival_day, strict=True)):
        tot[d] = tot.get(d, 0.0) + dem.get((d, c, a), 0.0)
    p = plan.plan.assign(c=plan.plan.batch_id.map(com))
    fill = {d: p[p.dest_id == d].kg.sum() / t for d, t in tot.items() if t > TOL}
    avg = sum(fill.values()) / len(fill)
    for d, f in fill.items():
        assert f + plan.solver["slack_usage"].get(d, 0.0) >= config.PHI_BALANCE * avg - 1e-4


def test_no_incumbent_falls_back(monkeypatch):
    s = sc()
    monkeypatch.setattr(milp, "_solve", lambda *a, **k: (None, {"status": "TimeLimit"}))
    plan = MilpPolicy().plan(s)
    assert plan.solver["fallback_used"] is True and len(plan.plan) > 0
    assert plan.solver["slack_usage"] == {} and plan.solver["mip_gap"] is None


def _kg_by_key(plan, s):
    com = s.tables["batches"].set_index("batch_id").commodity
    p = plan.plan.assign(c=plan.plan.batch_id.map(com))
    return p.groupby(["dest_id", "c", "arrival_day"]).kg.sum()


def test_demand_cap_override(monkeypatch):
    s = sc()
    key = _kg_by_key(MilpPolicy().plan(s), s).idxmax()
    ctx = {"demand_cap_override": {key: 0.0}}
    assert _kg_by_key(MilpPolicy().plan(s, ctx), s).get(key, 0.0) <= TOL
    monkeypatch.setattr(milp, "_solve", lambda *a, **k: (None, {"status": "forced"}))
    assert _kg_by_key(MilpPolicy().plan(s, ctx), s).get(key, 0.0) <= TOL  # greedy honours it


def test_plan_trips_export():
    s = sc()
    plan = MilpPolicy().plan(s)
    p, tr = plan.plan, plan.trips
    assert tr.trip_id.is_unique and set(p.trip_id) == set(tr.trip_id)
    assert (tr.kg_total <= tr.capacity_kg + TOL).all()
    per_trip = p.groupby("trip_id").kg.sum()
    assert ((per_trip - tr.set_index("trip_id").kg_total[per_trip.index]).abs() < TOL).all()
    ranks = sorted(p.priority_rank.unique())
    assert ranks == list(range(1, len(ranks) + 1)) and p.priority_rank.is_monotonic_increasing
    score = p.drop_duplicates("priority_rank").priority_score
    assert (score.diff().dropna() <= TOL).all()


def test_aggregation_fallback_valid(tmp_path):
    """U-02: the scale fallback (forced via agg_threshold) yields a plan with 0 validator
    violations; the default threshold leaves tiny_3batch on the batch-level path."""
    from freshroute.generator import generate
    from validator.validate import validate

    assert "aggregation" not in MilpPolicy().plan(sc()).solver
    s = load_scenario(generate("agg", 7, 60, 3, 2, 2, tmp_path))
    plan = MilpPolicy().plan(s, {"agg_threshold": 0})
    agg = plan.solver["aggregation"]
    assert agg["groups"] < agg["batches"] == 60 and agg["validator_violations"] == 0
    assert not plan.solver["fallback_used"] and validate(s, plan.plan).violation_total == 0
    check_valid(plan, s)


def test_aggregation_pools_fleet(tmp_path):
    """U-02/A-46: identical vehicles pool into classes, trips land on concrete vehicles."""
    from freshroute.generator import generate
    from validator.validate import validate

    s = load_scenario(generate("aggv", 7, 60, 3, 2, 12, tmp_path))
    plan = MilpPolicy().plan(s, {"agg_threshold": 0})
    agg = plan.solver["aggregation"]
    assert agg["vehicle_classes"] < 12 and agg["unassigned_kg"] < config.FLOAT_TOL
    assert set(plan.plan.vehicle_id) <= set(s.tables["vehicles"].vehicle_id)
    assert not plan.solver["fallback_used"] and validate(s, plan.plan).violation_total == 0
