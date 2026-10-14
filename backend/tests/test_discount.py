"""tiered markdown rule (ARCHITECTURE.md section 10, A-22)."""
from pathlib import Path

import pandas as pd
import pytest

from freshroute.config import FLOAT_TOL
from freshroute.discount import build_discounts, delta_revenue, discount_pct, tier_index
from freshroute.io import load_scenario

TIERS = [0, 10, 20, 35]
# stock 1000 / demand 100 / eps 3: tiers 10 and 20 pass the worth-it test, 35 does not
KW = dict(stock_kg=1000, demand_kg=100, price=30, elasticity=3.0, salvage=3, max_discount_frac=0.35)


def d(risk, hours=100, **over):
    return discount_pct(risk, hours, **{**KW, **over})


@pytest.mark.parametrize("risk,tier", [(0.09, 0), (0.10, 10), (0.29, 10), (0.30, 20),
                                       (0.50, 20), (0.51, 35), (0.0, 0), (1.0, 35)])
def test_tier_boundaries(risk, tier):
    assert TIERS[tier_index(risk)] == tier
    assert d(risk).tier_base_pct == tier


def test_time_trigger_steps_up_one_tier():
    assert d(0.05, 24).tier_after_time_trigger_pct == 10
    assert d(0.20, 24).tier_after_time_trigger_pct == 20
    assert d(0.30, 24).tier_after_time_trigger_pct == 35
    assert d(0.20, 24.5).tier_after_time_trigger_pct == 10
    assert d(0.90, 10).tier_after_time_trigger_pct == 35  # 35 stays 35


def test_max_discount_cap():
    r = d(0.9, max_discount_frac=0.20)
    assert r.capped_by == "max_discount"
    assert r.discount_pct == pytest.approx(20)


def test_salvage_floor():
    r = d(0.9, price=30, salvage=25)  # cap = 1 - 25/30 = 16.67 %
    assert r.capped_by == "salvage_floor"
    assert r.discount_pct == pytest.approx(100 * (1 - 25 / 30))
    assert 30 * (1 - r.discount_pct / 100) >= 25 - FLOAT_TOL


def test_worth_it_falls_back_to_lower_tier_then_zero():
    r = d(0.9)  # 35 % fails, 20 % passes
    assert r.discount_pct == pytest.approx(20) and r.applied and r.delta_revenue_inr > 0
    r = d(0.9, elasticity=0.0)  # no uplift: every markdown loses money
    assert r.discount_pct == 0 and not r.applied
    assert delta_revenue(1000, 100, 30, 0.0, 0.1) < 0


def test_monotone_in_risk_and_time():
    prev = -1.0
    for i in range(101):
        cur = d(i / 100).tier_base_pct
        assert cur >= prev - FLOAT_TOL
        prev = cur
    for risk in (0.0, 0.2, 0.4, 0.8):
        prev = -1.0
        for h in range(120, -1, -6):
            cur = d(risk, h).tier_after_time_trigger_pct
            assert cur >= prev - FLOAT_TOL
            prev = cur


def test_build_discounts_per_lot_monotone_and_capped():
    sc = load_scenario(Path(__file__).parent / "fixtures" / "tiny_3batch")
    plan = pd.DataFrame([
        dict(batch_id="B2", dest_id="D1",
             arrival_h=10.0, arrival_day=0, kg=500, usable_life_at_arrival_h=50.0),
        dict(batch_id="B1", dest_id="D1",
             arrival_h=29.0, arrival_day=1, kg=1000, usable_life_at_arrival_h=70.0),
        dict(batch_id="B3", dest_id="D2",
             arrival_h=12.0, arrival_day=0, kg=800, usable_life_at_arrival_h=400.0),
    ])
    out = build_discounts(sc, plan)
    assert not out.empty and out["lot_id"].str.count("@").eq(2).all()
    comm = sc.tables["commodities"].set_index("commodity")
    for _, g in out.groupby("lot_id"):
        assert (g["discount_pct"].diff().dropna() >= -FLOAT_TOL).all()
    for r in out.itertuples():
        assert r.discount_pct <= comm.loc[r.commodity, "max_discount_frac"] * 100 + FLOAT_TOL
    pd.testing.assert_frame_equal(out, build_discounts(sc, plan))  # deterministic
    # float arrival_day (arcs with NaN rows, e.g. practice) must still give "<b>@<d>@<int day>"
    flt = build_discounts(sc, plan.astype({"arrival_day": float}))
    assert set(flt.lot_id) == set(out.lot_id) and not flt.lot_id.str.endswith(".0").any()
