"""Independent hard-violation rules (ARCHITECTURE.md section 11; maths of section 7 re-implemented
here on purpose, D-04). Imports only stdlib and pandas."""
from __future__ import annotations

from collections import defaultdict

import pandas as pd

TOL = 1e-6  # validator's own tolerance; deliberately not imported from freshroute.config
PCT = 100.0  # discounts.csv is in percent; commodities carry fractions (io.py converts)


def v(code: str, detail: str, shipment_id=None, observed=None, limit=None) -> dict:
    return {"code": code, "shipment_id": shipment_id, "detail": detail,
            "observed": observed, "limit": limit}


def usable_life(rsl, wait_h, travel_h, handling_h, t_store, t_transit, ref, q10) -> float:
    """RSL - wait*decay(store) - travel*decay(transit) - handling (section 7)."""
    return (rsl - wait_h * q10 ** ((t_store - ref) / 10)
            - travel_h * q10 ** ((t_transit - ref) / 10) - handling_h)


def _in_window(arrival_h: float, d, mode: str) -> bool:
    h = arrival_h % 24 if mode == "daily" else arrival_h
    return d["window_open_h"] - TOL <= h <= d["window_close_h"] + TOL


def _slots(s) -> set[float]:
    return set() if pd.isna(s) else {float(x) for x in str(s).split("|")}


def shipment_rules(t: dict, plan: pd.DataFrame, window_mode: str) -> list[dict]:
    """Per-row rules plus the aggregates over batches, trips and receiving days."""
    b = t["batches"].set_index("batch_id")
    c = t["commodities"].set_index("commodity")
    dst = t["destinations"].set_index("dest_id")
    veh = t["vehicles"].set_index("vehicle_id")
    lanes = t["lanes"].set_index(["origin", "dest_id", "mode"])
    out: list[dict] = []
    shipped = defaultdict(float)
    trip_kg, trip_veh, trip_day = defaultdict(float), {}, {}
    recv = defaultdict(float)
    for r in plan.sort_values("shipment_id").to_dict("records"):
        sid = r["shipment_id"]
        bad = [f"{k}={r[k]}" for k, tab in (("batch_id", b), ("dest_id", dst), ("vehicle_id", veh))
               if r[k] not in tab.index]
        if bad:
            out.append(v("UNKNOWN_ID", "unknown " + ", ".join(bad), sid))
            continue
        kg = float(r["kg"])
        if kg <= 0:
            out.append(v("NEGATIVE_QTY", f"kg={kg} must be > 0", sid, kg, 0.0))
            continue
        bt, ve, d = b.loc[r["batch_id"]], veh.loc[r["vehicle_id"]], dst.loc[r["dest_id"]]
        shipped[r["batch_id"]] += kg
        disp = float(r["dispatch_h"])
        if disp < bt["available_from_h"] - TOL:
            out.append(v("NOT_AVAILABLE", "dispatch before batch available_from_h", sid,
                         disp, float(bt["available_from_h"])))
        if disp < ve["available_from_h"] - TOL:
            out.append(v("VEHICLE_AVAILABILITY", "dispatch before vehicle available_from_h", sid,
                         disp, float(ve["available_from_h"])))
        if ve["mode"] != r["mode"]:
            out.append(v("MODE_MISMATCH", f"plan mode {r['mode']} != vehicle mode {ve['mode']}",
                         sid))
        key = (bt["origin_hub"], r["dest_id"], r["mode"])
        if ve["origin"] != bt["origin_hub"] or key not in lanes.index:
            out.append(v("NO_LANE", f"no lane {key} / vehicle origin {ve['origin']}", sid))
        else:
            ln = lanes.loc[key]
            if r["mode"] == "rail" and (disp % 24) not in _slots(ln["departure_slots"]):
                out.append(v("RAIL_SLOT", "dispatch hour-of-day not in departure_slots", sid,
                             disp % 24))
            arr = disp + float(ln["travel_h_p50"])
            cm = c.loc[bt["commodity"]]
            u = usable_life(bt["remaining_shelf_life_h"], disp - bt["available_from_h"],
                            ln["travel_h_p50"], d["handling_time_h"], bt["storage_temp_c"],
                            ln["transit_temp_c"], cm["ref_temp_c"], cm["q10"])
            if u < cm["min_sell_window_h"] - TOL:
                out.append(v("SHELF_LIFE", "usable life at arrival below min sell window", sid,
                             float(u), float(cm["min_sell_window_h"])))
            if not _in_window(arr, d, window_mode):
                out.append(v("DELIVERY_WINDOW", f"arrival_h {arr} outside window", sid, arr,
                             float(d["window_close_h"])))
            recv[(r["dest_id"], int(arr // 24))] += kg
        tid = r["trip_id"]
        trip_kg[tid] += kg
        trip_veh[tid] = r["vehicle_id"]
        trip_day[tid] = int(disp // 24)
    for bid, kg in sorted(shipped.items()):
        if kg > b.loc[bid, "qty_kg"] + TOL:
            out.append(v("STOCK_OVERDRAW", f"batch {bid} shipped more than qty_kg", None, kg,
                         float(b.loc[bid, "qty_kg"])))
    per_day = defaultdict(set)
    for tid, kg in sorted(trip_kg.items()):
        cap = float(veh.loc[trip_veh[tid], "capacity_kg"])
        if kg > cap + TOL:
            out.append(v("VEHICLE_CAPACITY", f"trip {tid} over capacity", None, kg, cap))
        per_day[(trip_veh[tid], trip_day[tid])].add(tid)
    for (vid, day), tids in sorted(per_day.items()):
        lim = float(veh.loc[vid, "max_trips_day"])
        if len(tids) > lim:
            out.append(v("VEHICLE_TRIPS_PER_DAY", f"{vid} runs {len(tids)} trips on day {day}",
                         None, len(tids), lim))
    for (did, day), kg in sorted(recv.items()):
        cap = float(dst.loc[did, "receive_cap_kg_day"])
        if kg > cap + TOL:
            out.append(v("RECEIVING_CAPACITY", f"{did} receives too much on day {day}", None,
                         kg, cap))
    return out


def discount_rules(t: dict, disc: pd.DataFrame) -> list[dict]:
    out: list[dict] = []
    c = t["commodities"].set_index("commodity")
    p = t["prices"].set_index(["dest_id", "commodity", "day"])
    b = t["batches"].set_index("batch_id")
    dst = set(t["destinations"]["dest_id"])
    last: dict[str, float] = {}
    for r in disc.sort_values(["lot_id", "day"]).to_dict("records"):
        if r["commodity"] not in c.index or r["dest_id"] not in dst or r["batch_id"] not in b.index:
            out.append(v("UNKNOWN_ID", f"discount lot {r['lot_id']} has unknown id"))
            continue
        d = float(r["discount_pct"])
        cm = c.loc[r["commodity"]]
        if d > cm["max_discount_frac"] * PCT + TOL:
            out.append(v("DISCOUNT_CAP", f"lot {r['lot_id']} day {r['day']}", None, d,
                         float(cm["max_discount_frac"] * PCT)))
        k = (r["dest_id"], r["commodity"], int(r["day"]))
        if k in p.index:
            net = p.loc[k, "price_inr_kg"] * (1 - d / PCT)
            if net < cm["salvage_value_inr_kg"] - TOL:
                out.append(v("DISCOUNT_BELOW_SALVAGE", f"lot {r['lot_id']} day {r['day']}", None,
                             float(net), float(cm["salvage_value_inr_kg"])))
        if r["lot_id"] in last and d < last[r["lot_id"]] - TOL:
            out.append(v("DISCOUNT_NOT_MONOTONE", f"lot {r['lot_id']} day {r['day']}", None, d,
                         last[r["lot_id"]]))
        last[r["lot_id"]] = d
    return out


def demand_warnings(t: dict, plan: pd.DataFrame, slack: float) -> list[dict]:
    """DEMAND_CAP_EXCEEDED: kg per (dest, commodity, arrival day) over p50 * (1 + slack)."""
    b = t["batches"].set_index("batch_id")
    dem = t["demand"].set_index(["dest_id", "commodity", "day"])["demand_kg_p50"]
    lanes = t["lanes"].set_index(["origin", "dest_id", "mode"])["travel_h_p50"]
    agg: dict = defaultdict(float)
    for r in plan.to_dict("records"):
        if r["batch_id"] not in b.index or r["kg"] <= 0:
            continue
        tr = lanes.get((b.loc[r["batch_id"], "origin_hub"], r["dest_id"], r["mode"]))
        if tr is not None:
            k = (r["dest_id"], b.loc[r["batch_id"], "commodity"], int((r["dispatch_h"] + tr) // 24))
            agg[k] += r["kg"]
    return [{"code": "DEMAND_CAP_EXCEEDED", "detail": f"{k}: {kg} kg > cap"}
            for k, kg in sorted(agg.items())
            if k in dem.index and kg > dem[k] * (1 + slack) + TOL]
