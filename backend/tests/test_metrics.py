"""metrics.compute and the DATABASE.md section 5.7 invariants."""
import json
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from freshroute.config import FLOAT_TOL
from freshroute.metrics import compute

FIXTURE = Path(__file__).parent / "fixtures" / "metrics_example.json"


def near(a, b):
    assert a == pytest.approx(b, abs=FLOAT_TOL)


def check_invariants(m):
    e, v, k, sb = m["economics_inr"], m["volumes_kg"], m["kpis"], m["spoilage_breakdown_kg"]
    near(e["revenue"], e["gross_revenue_at_list"] - e["discount_cost"])
    near(e["net"], e["revenue"] - e["transport"] - e["handling"] - e["spoilage_cost"])
    near(k["net_inr"], e["net"])
    near(k["spoilage_kg"], sum(sb.values()))
    near(v["total_supply"], v["sold"] + k["spoilage_kg"] + v["carryover"]["total"])
    near(v["total_supply"], v["shipped"] + v["unshipped"])
    near(v["carryover"]["total"], v["carryover"]["destination"] + v["carryover"]["origin"])
    near(k["spoilage_pct"], k["spoilage_kg"] / v["total_supply"] * 100)


def test_fixture_invariants():
    check_invariants(json.loads(FIXTURE.read_text()))


def _scenario():
    t = {
        "commodities": pd.DataFrame([{"commodity": "tomato", "unit_cost_inr_kg": 10.0,
                                      "disposal_cost_inr_kg": 1.0, "salvage_value_inr_kg": 3.0}]),
        "batches": pd.DataFrame([{"batch_id": "B1", "commodity": "tomato", "origin_hub": "H",
                                  "qty_kg": 1000.0}]),
        "destinations": pd.DataFrame([{"dest_id": "D1", "handling_cost_inr_kg": 2.0}]),
        "lanes": pd.DataFrame([{"origin": "H", "dest_id": "D1", "mode": "reefer",
                                "cost_fixed_inr_trip": 500.0, "cost_var_inr_kg": 3.0}]),
        "vehicles": pd.DataFrame([{"vehicle_id": "V1", "capacity_kg": 1000.0}]),
    }
    return SimpleNamespace(tables=t, meta={"name": "hand"})


def test_hand_built():
    plan = pd.DataFrame([{"batch_id": "B1", "dest_id": "D1", "trip_id": "T1",
                          "vehicle_id": "V1", "mode": "reefer", "kg": 800.0}])
    ledger = pd.DataFrame([{
        "dest_id": "D1", "commodity": "tomato", "day": 0, "base_demand_kg": 700.0,
        "delivered_kg": 800.0, "handling_loss_kg": 40.0, "sold_kg": 600.0, "price_inr_kg": 50.0,
        "discount_frac": 0.1, "unsold_expired_kg": 100.0, "carryover_kg": 60.0}])
    origin = pd.DataFrame([{"batch_id": "B1", "expired_kg": 50.0, "carryover_kg": 150.0}])
    m = compute(_scenario(), plan, pd.DataFrame(), {"ledger": ledger, "origin": origin})
    check_invariants(m)
    want = dict(gross_revenue_at_list=30000, discount_cost=3000, revenue=27000,
                transport=2900, handling=1600, spoilage_cost=1520, net=20980)
    for key, val in want.items():
        near(m["economics_inr"][key], val)
    near(m["kpis"]["spoilage_kg"], 190)
    near(m["kpis"]["demand_fulfillment_pct"], 600 / 700 * 100)
    assert m["trips"]["count"] == 1
    near(m["trips"]["avg_utilization_pct"], 80)
