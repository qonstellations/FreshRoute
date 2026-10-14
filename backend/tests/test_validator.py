"""validator accepts the hand-built plan, flags each injected violation, stays independent
(ARCHITECTURE.md section 11)."""
import ast
import copy
import dataclasses
import json
from pathlib import Path

import pandas as pd
import pytest

from freshroute.io import load_scenario
from validator.validate import validate

ROOT = Path(__file__).parent
FIX = ROOT / "fixtures" / "tiny_3batch"
EXP = FIX / "expected"
ALLOWED = {"pandas", "numpy", "freshroute.schema", "freshroute.io", "validator"}


def base():
    sc = load_scenario(FIX)
    return sc, pd.read_csv(EXP / "plan.csv"), pd.read_csv(EXP / "discounts.csv")


def codes(sc, plan, disc=None):
    return {x["code"] for x in validate(sc, plan, disc).violations}


def mut(sc, table, where, **cols):
    """Copy of sc with `cols` set on rows of `table` matching the pandas query `where`."""
    tabs = copy.deepcopy(sc.tables)
    df = tabs[table]
    for k, val in cols.items():
        df[k] = df[k].astype(object) if isinstance(val, str) else df[k]
        df.loc[df.eval(where), k] = val
    return dataclasses.replace(sc, tables=tabs)


def test_expected_plan_is_clean():
    sc, plan, disc = base()
    rep = validate(sc, plan, disc, overship_slack=0.05)
    assert rep.violation_total == 0 and rep.warnings == []
    assert rep.to_dict()["counts"] == {}


def test_expected_trips_and_metrics_consistent():
    _, plan, _ = base()
    trips = pd.read_csv(EXP / "trips.csv")
    got = plan.groupby("trip_id")["kg"].sum().to_dict()
    assert got == trips.set_index("trip_id")["kg_total"].to_dict()
    m = json.loads((EXP / "metrics.json").read_text())
    e, v = m["economics_inr"], m["volumes_kg"]
    assert e["net"] == (e["revenue"] - e["cost_of_goods_sold"] - e["transport"] - e["handling"]
                         - e["spoilage_cost"])
    assert v["total_supply"] == v["sold"] + m["kpis"]["spoilage_kg"] + v["carryover"]["total"]
    assert m["kpis"]["spoilage_kg"] == sum(m["spoilage_breakdown_kg"].values())


def test_validation_json_written(tmp_path):
    sc, plan, disc = base()
    validate(sc, plan, disc).write(tmp_path / "validation.json")
    d = json.loads((tmp_path / "validation.json").read_text())
    assert d == {"schema_version": 2, "violation_total": 0, "counts": {}, "violations": [],
                 "warnings": []}


def test_demand_cap_warning_only():
    sc, plan, _ = base()
    plan.loc[plan.shipment_id == "S0003", "kg"] = 500  # D2 tomato demand 350
    rep = validate(sc, plan, overship_slack=0.05)
    assert rep.violation_total == 0
    assert [w["code"] for w in rep.warnings] == ["DEMAND_CAP_EXCEEDED"]


def _plan_case(code):
    sc, plan, _ = base()
    s3 = plan.shipment_id == "S0003"
    if code == "UNKNOWN_ID":
        plan.loc[s3, "batch_id"] = "ZZ"
    elif code == "NEGATIVE_QTY":
        plan.loc[s3, "kg"] = -5
    elif code == "STOCK_OVERDRAW":
        plan.loc[s3, "kg"] = 501
    elif code == "NOT_AVAILABLE":
        sc = mut(sc, "batches", "batch_id == 'B1'", available_from_h=10)
    elif code == "NO_LANE":
        sc = dataclasses.replace(sc, tables={**sc.tables, "lanes": sc.tables["lanes"].iloc[:1]})
    elif code == "MODE_MISMATCH":
        amb = sc.tables["lanes"].assign(mode="ambient")
        sc = dataclasses.replace(
            sc, tables={**sc.tables, "lanes": pd.concat([sc.tables["lanes"], amb])})
        plan.loc[s3, "mode"] = "ambient"
    elif code == "RAIL_SLOT":
        sc = mut(sc, "vehicles", "vehicle_id == 'V1'", mode="rail")
        sc = mut(sc, "lanes", "dest_id == 'D1'", mode="rail", departure_slots="18|22")
        plan["mode"] = ["rail", "rail", "reefer", "reefer"]
        # D2 rows stay reefer: give them their own reefer vehicle
        sc.tables["vehicles"] = pd.concat([sc.tables["vehicles"], sc.tables["vehicles"].assign(
            vehicle_id="V2", mode="reefer")])
        plan.loc[plan.dest_id == "D2", "vehicle_id"] = "V2"
    elif code == "SHELF_LIFE":
        sc = mut(sc, "batches", "batch_id == 'B2'", remaining_shelf_life_h=30)
    elif code == "DELIVERY_WINDOW":
        sc = mut(sc, "destinations", "dest_id == 'D1'", window_close_h=10)
    elif code == "VEHICLE_CAPACITY":
        sc = mut(sc, "vehicles", "vehicle_id == 'V1'", capacity_kg=650)
    elif code == "VEHICLE_TRIPS_PER_DAY":
        sc = mut(sc, "vehicles", "vehicle_id == 'V1'", max_trips_day=1)
    elif code == "VEHICLE_AVAILABILITY":
        sc = mut(sc, "vehicles", "vehicle_id == 'V1'", available_from_h=10)
    elif code == "RECEIVING_CAPACITY":
        sc = mut(sc, "destinations", "dest_id == 'D1'", receive_cap_kg_day=600)
    return sc, plan


@pytest.mark.parametrize("code", [
    "UNKNOWN_ID", "NEGATIVE_QTY", "STOCK_OVERDRAW", "NOT_AVAILABLE", "NO_LANE", "MODE_MISMATCH",
    "RAIL_SLOT", "SHELF_LIFE", "DELIVERY_WINDOW", "VEHICLE_CAPACITY", "VEHICLE_TRIPS_PER_DAY",
    "VEHICLE_AVAILABILITY", "RECEIVING_CAPACITY"])
def test_injected_plan_violation(code):
    sc, plan = _plan_case(code)
    assert codes(sc, plan) == {code}


def _disc(rows):
    cols = ["lot_id", "dest_id", "commodity", "batch_id", "day", "discount_pct"]
    return pd.DataFrame(rows, columns=cols)


def test_injected_discount_cap():
    sc, plan, _ = base()
    d = _disc([("B1@D1@0", "D1", "tomato", "B1", 0, 40)])  # max 35
    assert codes(sc, plan, d) == {"DISCOUNT_CAP"}


def test_injected_discount_below_salvage():
    sc, plan, _ = base()
    sc = mut(sc, "commodities", "commodity == 'onion'", salvage_value_inr_kg=17.0)
    d = _disc([("B3@D1@0", "D1", "onion", "B3", 0, 20)])  # 20 * 0.8 = 16 < 17, cap 20 ok
    assert codes(sc, plan, d) == {"DISCOUNT_BELOW_SALVAGE"}


def test_injected_discount_not_monotone():
    sc, plan, _ = base()
    d = _disc([("B1@D1@0", "D1", "tomato", "B1", 1, 10), ("B1@D1@0", "D1", "tomato", "B1", 2, 5)])
    assert codes(sc, plan, d) == {"DISCOUNT_NOT_MONOTONE"}


def test_validator_imports_only_allowed_modules():
    files = list((ROOT.parent / "src" / "validator").glob("*.py"))
    assert files
    for f in files:
        for node in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                mods = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                mods = [node.module]
            else:
                continue
            for m in mods:
                ok = m.split(".")[0] in {"__future__", "json", "collections", "dataclasses",
                                         "pathlib"} or any(
                    m == a or m.startswith(a + ".") for a in ALLOWED)
                assert ok, f"{f.name} imports {m}"
