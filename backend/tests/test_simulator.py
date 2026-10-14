"""Simulator on tiny_3batch with a hand-built plan. Arithmetic in comments."""
from pathlib import Path

import pandas as pd
import pytest

from freshroute.io import load_scenario
from freshroute.metrics import compute
from freshroute.simulator import simulate
from test_metrics import check_invariants, near

SC = load_scenario(Path(__file__).parent / "fixtures" / "tiny_3batch")

# Dispatch at h=5, store 20C (decay 1), transit 10C (decay 0.5), handling 2 h.
# S1 B2->D1 500 kg: arrive 5+12=17 (day 0); life 60-5-12*.5-2=47; expiry 64
# S2 B1->D1 600 kg: arrive 17; life 100-5-6-2=87; expiry 104
# S3 B3->D2 400 kg onion: arrive 5+18=23; life 400-5-9-2=384; expiry 407
PLAN = pd.DataFrame([
    dict(batch_id="B2", dest_id="D1", trip_id="T1", vehicle_id="V1", mode="reefer",
         kg=500.0, arrival_h=17.0, arrival_day=0, usable_life_at_arrival_h=47.0),
    dict(batch_id="B1", dest_id="D1", trip_id="T1", vehicle_id="V1", mode="reefer",
         kg=600.0, arrival_h=17.0, arrival_day=0, usable_life_at_arrival_h=87.0),
    dict(batch_id="B3", dest_id="D2", trip_id="T2", vehicle_id="V1", mode="reefer",
         kg=400.0, arrival_h=23.0, arrival_day=0, usable_life_at_arrival_h=384.0),
])
L2, L1 = "B2@D1@0", "B1@D1@0"
DISC = pd.DataFrame([  # L2 head on days 1-2 (day 2 it is empty, so L1's 20 % applies)
    dict(lot_id=L2, day=1, discount_pct=10.0), dict(lot_id=L2, day=2, discount_pct=35.0),
    dict(lot_id=L1, day=2, discount_pct=20.0)])


def test_hand_checked():
    sim = simulate(SC, PLAN, DISC)
    led = sim["ledger"].set_index(["dest_id", "commodity", "day"])
    # D1 tomato: stock L2 = 500*.975 = 487.5 (loss 12.5), L1 = 600*.975 = 585 (loss 15)
    # d0: no discount, eff 400, sell 400 from L2 (87.5 left)
    # d1: head L2 -> 10 %, eff 400*(1+1.0*.1)=440: 87.5 from L2 + 352.5 from L1 (232.5 left)
    # d2: L2 empty so head L1 -> 20 %, eff 480, sell 232.5
    d1 = led.loc[("D1", "tomato")]
    assert list(d1.sold_kg) == pytest.approx([400, 440, 232.5])
    assert list(d1.discount_frac) == pytest.approx([0, 0.1, 0.2])
    near(d1.handling_loss_kg.sum(), 27.5)
    near(d1.delivered_kg.sum(), 1100)
    # D2 onion: 400*.99=396 (loss 4); 250 on d0, 146 on d1, none left
    assert list(led.loc[("D2", "onion")].sold_kg) == pytest.approx([250, 146, 0])
    # origin: B1 400 and B3 400 unshipped, expiry 100 / 400 h > 72 -> carry-over
    near(sim["origin"].carryover_kg.sum(), 800)
    near(sim["origin"].expired_kg.sum(), 0)

    m = compute(SC, PLAN, DISC, sim)
    check_invariants(m)
    e = m["economics_inr"]
    # gross = 400*30 + 440*30 + 232.5*30 + 396*22 = 12000+13200+6975+8712 = 40887
    # discount = 1320 + 1395 = 2715 ; revenue 38172
    # transport = (2000+1100*2.0) + (2500+400*2.5) = 4200+3500 = 7700
    # handling = 1100*1.0 + 400*1.5 = 1700 ; spoilage = 27.5*14 + 4*9 = 421
    # cogs = (400+440+232.5)*15 + 396*12 = 16087.5 + 4752 = 20839.5
    # net = 38172 - 20839.5 - 7700 - 1700 - 421 = 7511.5
    for key, val in dict(gross_revenue_at_list=40887, discount_cost=2715, revenue=38172,
                         cost_of_goods_sold=20839.5, transport=7700, handling=1700,
                         spoilage_cost=421, net=7511.5).items():
        near(e[key], val)
    near(m["kpis"]["spoilage_kg"], 31.5)
    near(m["kpis"]["demand_fulfillment_pct"], 1428.5 / 3900 * 100)


def test_mass_balance_and_expiry_under_realization():
    # D1 tomato demand 100/day: d0 sell 100 (L2 387.5); d1 10 % -> 110 (277.5);
    # d2 head L2 35 % -> eff 135 (142.5 left); L2 expiry 64 <= 72 -> 142.5 unsold expired;
    # L1 untouched 585 alive (expiry 104) -> carry-over.
    real = {"demand_kg": {("D1", "tomato", d): 100.0 for d in range(3)}}
    sim = simulate(SC, PLAN, DISC, real)
    led, lots = sim["ledger"], sim["lots"].set_index("lot_id")
    near(led.unsold_expired_kg.sum(), 142.5)
    near(lots.loc[L1, "kg_carryover"], 585)
    # mass balance: delivered = sold + handling loss + expired unsold + carry-over
    near(led.delivered_kg.sum(), PLAN.kg.sum())
    near(led.delivered_kg.sum(), led.sold_kg.sum() + led.handling_loss_kg.sum()
         + led.unsold_expired_kg.sum() + led.carryover_kg.sum())
    check_invariants(compute(SC, PLAN, DISC, sim))


def test_deterministic():
    a, b = simulate(SC, PLAN, DISC), simulate(SC, PLAN, DISC)
    pd.testing.assert_frame_equal(a["ledger"], b["ledger"])
    pd.testing.assert_frame_equal(a["origin"], b["origin"])
