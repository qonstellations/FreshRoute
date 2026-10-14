"""Seeded synthetic scenario generator, v3 (ARCHITECTURE.md section 5 and A-47..A-50;
DATABASE.md sections 3.1-3.10). SYNTHETIC: no organizer data and no Agmarknet snapshot, so
prices come from the static, report-grounded table below. Every scenario.json says so.

Structure (A-49): a Kolar/Chikkaballapur -> Bengaluru-region network with real node
coordinates. Lane times follow road distance, outlet type drives windows, prices, baskets
and receiving capacity, demand roughly matches supply and is only placed on days some lane
can actually deliver, and the fleet's trips per day follow its lane times.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from freshroute import schema as S
from freshroute.config import DISPATCH_HOUR, HOURS_PER_DAY, SCHEMA_VERSION

GENERATOR_VERSION = "v3"
PRICE_SOURCE = "static_table_generator_v3"
# [team] modal mandi prices, INR/kg, from published Agmarknet aggregates (Farmer.in CC-BY
# ticker + CEDA series, July 2026; keyless, NOT a data.gov.in snapshot).
STATIC_PRICE_INR_KG = {
    "tomato": 28.0, "spinach": 35.0, "banana": 32.0, "mango": 70.0, "onion": 24.0, "potato": 18.0,
}
PRICE_DAY_VOL = {  # [team] sd of the shared daily market move per commodity; onion swings most
    "tomato": 0.06, "spinach": 0.07, "banana": 0.04, "mango": 0.05, "onion": 0.09, "potato": 0.05,
}
PRICE_SPREAD = {  # [team] (min_ratio, max_ratio) of the day's price band
    "tomato": (0.90, 1.12), "spinach": (0.88, 1.15), "banana": (0.90, 1.12),
    "mango": (0.88, 1.15), "onion": (0.75, 1.30), "potato": (0.85, 1.20),
}
# [team] class, base shelf life h (at ref temp), ref C, q10, min sell window h, handling loss %,
# unit cost, disposal, salvage (INR/kg), elasticity, max discount %. Unit cost ~ 55-60 % of the
# mandi modal price (farm-gate share); shelf lives are ambient Indian supply-chain figures, so
# leafy and soft produce expire inside a 2-3 day horizon while onion and potato do not (A-47).
_COMM = {
    "tomato": ("very_high", 144, 20, 2.5, 24, 3.0, 16, 2, 3, 1.0, 35),
    "spinach": ("very_high", 48, 20, 3.0, 12, 4.0, 20, 2, 1, 1.2, 40),
    "banana": ("high", 168, 20, 2.2, 24, 2.0, 18, 2, 5, 0.8, 30),
    "mango": ("high", 144, 25, 2.5, 24, 3.0, 40, 3, 10, 0.8, 30),
    "onion": ("low", 1440, 25, 1.8, 48, 1.0, 14, 1, 4, 0.5, 20),
    "potato": ("low", 1680, 25, 1.8, 48, 1.0, 10, 1, 4, 0.5, 20),
}
# [team] commodity mix ~ NABCONS production shares (potato/onion heavy; spinach has no NABCONS
# row and stays a minor leafy line). Must sum to 1.
_COMM_W = {"tomato": 0.16, "spinach": 0.06, "banana": 0.20, "mango": 0.12,
           "onion": 0.18, "potato": 0.28}
# [team] where each commodity waits at the hub (C): cold room or ambient shed, drawn per batch
STORAGE_TEMP_C = {"tomato": (22.0, 28.0), "spinach": (8.0, 22.0), "banana": (18.0, 22.0),
                  "mango": (26.0, 30.0), "onion": (28.0, 32.0), "potato": (4.0, 25.0)}
RSL_BETA = (5.0, 2.0)  # [team] remaining-life fraction of base ~ Beta(5, 2): mean 0.71
GRADE_A_MIN_FRAC = 0.6  # [team] grade A iff remaining-life fraction >= this (one variable)
RSL_BAND = (0.08, 0.20)  # [team] p10/p90 = rsl * (1 -/+ U(band))
QTY_LOGNORMAL = (math.log(250.0), 0.6)  # [team] batch kg ~ lognormal, median 250 kg
QTY_CLIP_KG = (40.0, 1500.0)

# Network (A-49). Coordinates are the real places, rounded; names are labels only.
HUBS = (("HUB1", "Kolar APMC aggregation point", 13.1360, 78.1290),
        ("HUB2", "Chikkaballapur aggregation point", 13.4355, 77.7315))
_ALL = ("banana", "mango", "onion", "potato", "spinach", "tomato")
_HORECA = ("banana", "onion", "potato", "spinach", "tomato")
_LONG_HAUL = ("banana", "mango", "onion", "potato", "tomato")  # no leafy on 300+ km trips
DESTS = (  # id, name, type, lat, lon, basket; the first n are used, in this order
    ("D1", "KR Market mandi, Bengaluru", "mandi", 12.9634, 77.5772, _ALL),
    ("D2", "Hoskote retail DC", "retail_DC", 13.0707, 77.7982, _ALL),
    ("D3", "Whitefield HoReCa cluster", "HoReCa", 12.9698, 77.7500, _HORECA),
    ("D4", "Tumakuru food processor", "processor", 13.3409, 77.1010, ("mango", "tomato")),
    ("D5", "Koyambedu market, Chennai", "mandi", 13.0694, 80.1948, _LONG_HAUL),
    ("D6", "Mysuru retail DC", "retail_DC", 12.2958, 76.6394, _ALL),
    ("D7", "Bowenpally market, Hyderabad", "mandi", 17.4710, 78.4840, _LONG_HAUL),
    ("D8", "Electronic City HoReCa cluster", "HoReCa", 12.8452, 77.6602, _HORECA),
)
# [team] outlet type -> daily receiving window (hour of day), price premium vs mandi, demand
# scale, receiving headroom over mean daily demand, handling h, handling INR/kg
DEST_TYPE = {
    "mandi": ((2.0, 14.0), 1.00, 1.5, 1.6, 1.0, 1.0),
    "retail_DC": ((4.0, 20.0), 1.20, 1.0, 1.25, 2.0, 1.5),
    "HoReCa": ((6.0, 16.0), 1.35, 0.4, 1.2, 1.0, 2.0),
    "processor": ((0.0, 24.0), 0.75, 0.8, 1.5, 3.0, 0.6),
}
ROAD_FACTOR = 1.3  # [team] road km / great-circle km
ROAD_SPEED_KMH = 40.0  # [team] loaded truck average incl. city stretches
ROAD_LOAD_H = 0.5  # [team] loading + gate time per trip
RAIL_MIN_KM = 200.0  # [team] rail lanes only to destinations this far (great circle)
RAIL_FACTOR, RAIL_SPEED_KMH, RAIL_DWELL_H = 1.2, 45.0, 6.0  # [team] parcel-van service
RAIL_SLOTS = "18|22"
TRAVEL_P90_RATIO = {"road": (1.15, 1.40), "rail": (1.20, 1.60)}  # [team] p90 / p50 draw
TRANSIT_TEMP_C = {"reefer": 12.0, "ambient": 30.0, "rail": 28.0}  # [team] mixed-load reefer
# [team] lane cost: fixed INR/trip = base + per road km; variable INR/kg = base + per road km
LANE_COST = {"reefer": (800.0, 40.0, 0.5, 0.004), "ambient": (500.0, 26.0, 0.4, 0.003),
             "rail": (2500.0, 0.0, 0.9, 0.0015)}
LANE_COST_NOISE = (0.9, 1.1)
VEHICLE_CAP_KG = (1000.0, 3000.0, 5000.0, 9000.0)  # [team] tempo, LCV, 5 t, 9 t truck
VEHICLE_CAP_P = (0.20, 0.35, 0.30, 0.15)
DUTY_H = 16.0  # [team] two-shift day; trips/day = floor(DUTY_H / round trip), at least 1
RAIL_CAP_KG, RAIL_TRIPS_DAY = 10000.0, 1  # one parcel-van booking per hub per day
# [team] demand: total p50 ~ U(ratio) x supply per commodity; destination share ~ type scale x
# lognormal(0, sd), capped at DEST_SHARE_CAP when at least 3 outlets take the commodity;
# daily multiplier AR(1) around 1.
DEMAND_SUPPLY_RATIO = (0.9, 1.1)
DEST_SHARE_SD = 0.35
DEST_SHARE_CAP = 0.35
DEMAND_AR = (0.5, 0.08)  # (persistence, shock sd)
_Q = {"very_high": (0.70, 1.35), "high": (0.75, 1.30), "low": (0.85, 1.15)}  # p10/p90 ratios
# [team] held-out hidden-style seeds: never tune against these; practice/small use seed 42.
HIDDEN_SEEDS = (101, 102, 103, 104, 201, 202, 203, 204, 205, 206)


def _r(x, n=2):
    return float(np.round(x, n))


def _km(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Great-circle distance (haversine), km."""
    la1, lo1, la2, lo2 = map(math.radians, (*a, *b))
    h = (math.sin((la2 - la1) / 2) ** 2
         + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2)
    return 2 * 6371.0 * math.asin(math.sqrt(h))


def _arrivals(lane, days: int) -> list[float]:
    """p50 arrival hour for a dispatch on each day (road at DISPATCH_HOUR, rail at the first
    slot after it); mirrors feasibility.build_arcs timing for batches ready at day start."""
    out = []
    for k in range(days):
        dep = k * HOURS_PER_DAY + DISPATCH_HOUR
        if lane["mode"] == "rail":
            dep = k * HOURS_PER_DAY + min(s for s in map(float, RAIL_SLOTS.split("|"))
                                          if s >= DISPATCH_HOUR)
        out.append(dep + lane["travel_h_p50"])
    return out


def generate(name: str, seed: int, n_batches: int, n_dests: int, days: int,
             n_vehicles: int, out_dir: str | Path,
             event_rows: list[tuple] | None = None) -> Path:
    """Write a complete scenario folder to `out_dir` and return it.

    `event_rows` holds `(event_id, type, target, magnitude, at_h)` tuples for
    event-bearing (hidden-style) scenarios; otherwise `events.csv` is empty.
    """
    if not 1 <= n_dests <= len(DESTS):
        raise ValueError(f"n_dests must be 1..{len(DESTS)}")
    rng = np.random.default_rng(seed)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    comms = sorted(_COMM)
    hubs = HUBS[:2 if n_dests > 4 else 1]
    dests = DESTS[:n_dests]

    commodities = pd.DataFrame([(c, *_COMM[c]) for c in comms], columns=list(S.COMMODITIES))

    # batches: remaining life ~ Beta share of base; grade follows from it; storage temp by
    # commodity; availability spread over the horizon
    rows = []
    for i in range(n_batches):
        c = comms[rng.choice(len(comms), p=[_COMM_W[x] for x in comms])]
        frac = float(rng.beta(*RSL_BETA))
        rsl = _r(_COMM[c][1] * frac)
        qty = _r(np.clip(rng.lognormal(*QTY_LOGNORMAL), *QTY_CLIP_KG))
        rows.append((
            f"B{i + 1:04d}", c, hubs[rng.integers(len(hubs))][0], qty, rsl,
            _r(rsl * (1 - rng.uniform(*RSL_BAND))), _r(rsl * (1 + rng.uniform(*RSL_BAND))),
            float(rng.choice(STORAGE_TEMP_C[c])), "A" if frac >= GRADE_A_MIN_FRAC else "B",
            float(HOURS_PER_DAY * rng.integers(0, days)),
        ))
    batches = pd.DataFrame(rows, columns=list(S.BATCHES))

    # lanes: reefer + ambient from every hub; rail to far destinations
    rows = []
    for h, _, hla, hlo in hubs:
        for d, _, _, dla, dlo, _ in dests:
            km = _km((hla, hlo), (dla, dlo))
            road = km * ROAD_FACTOR
            t = road / ROAD_SPEED_KMH + ROAD_LOAD_H
            p90 = rng.uniform(*TRAVEL_P90_RATIO["road"])
            for mode in ("reefer", "ambient"):
                fx, fkm, vb, vkm = LANE_COST[mode]
                rows.append((h, d, mode, _r(t), _r(t * p90),
                             _r((fx + fkm * road) * rng.uniform(*LANE_COST_NOISE), 0),
                             _r((vb + vkm * road) * rng.uniform(*LANE_COST_NOISE)),
                             TRANSIT_TEMP_C[mode], ""))
            if km >= RAIL_MIN_KM:
                rail = km * RAIL_FACTOR
                t = rail / RAIL_SPEED_KMH + RAIL_DWELL_H
                fx, _, vb, vkm = LANE_COST["rail"]
                rows.append((h, d, "rail", _r(t), _r(t * rng.uniform(*TRAVEL_P90_RATIO["rail"])),
                             fx, _r(vb + vkm * rail), TRANSIT_TEMP_C["rail"], RAIL_SLOTS))
    lanes = pd.DataFrame(rows, columns=list(S.LANES))
    lanes = lanes.sort_values(["origin", "dest_id", "mode"]).reset_index(drop=True)

    # fleet: both road modes at every hub; trips/day from the hub's median road lane
    rows = []
    for i in range(n_vehicles):
        h = hubs[i % len(hubs)][0]
        mode = "reefer" if (i // len(hubs)) % 2 == 0 else "ambient"
        med = float(lanes[(lanes.origin == h) & (lanes["mode"] == mode)].travel_h_p50.median())
        rows.append((f"V{i + 1}", h, mode, float(rng.choice(VEHICLE_CAP_KG, p=VEHICLE_CAP_P)),
                     0.0, max(1, int(DUTY_H // (2 * med)))))
    for i, (h, *_) in enumerate(hubs):
        if ((lanes.origin == h) & (lanes["mode"] == "rail")).any():
            rows.append((f"VR{i + 1}", h, "rail", RAIL_CAP_KG, 0.0, RAIL_TRIPS_DAY))
    vehicles = pd.DataFrame(rows, columns=list(S.VEHICLES))

    # reachable (dest, day): some lane with a vehicle arrives inside the daily window
    fleet = set(zip(vehicles.origin, vehicles["mode"], strict=True))
    reach: set = set()
    for ln in lanes.to_dict("records"):
        if (ln["origin"], ln["mode"]) not in fleet:
            continue
        lo, hi = DEST_TYPE[next(t for d, _, t, *_ in dests if d == ln["dest_id"])][0]
        for a in _arrivals(ln, days):
            if a // HOURS_PER_DAY < days and lo <= a % HOURS_PER_DAY <= hi:
                reach.add((ln["dest_id"], int(a // HOURS_PER_DAY)))

    # demand + prices
    supply = batches.groupby("commodity")["qty_kg"].sum()
    market = {c: np.cumprod(np.r_[1.0, 1 + rng.normal(0, PRICE_DAY_VOL[c], days - 1)])
              for c in comms}
    dnoise = {d: rng.uniform(0.95, 1.05) for d, *_ in dests}
    rows, prow = [], []
    for c in comms:
        q10r, q90r = _Q[_COMM[c][0]]
        smin, smax = PRICE_SPREAD[c]
        for d, _, typ, *_ in dests:
            for day in range(days):
                p = _r(STATIC_PRICE_INR_KG[c] * DEST_TYPE[typ][1] * dnoise[d] * market[c][day])
                prow.append((d, c, day, p, _r(p * smin), _r(p * smax)))
        cells = [(d, typ, day) for d, _, typ, _, _, basket in dests if c in basket
                 for day in range(days) if (d, day) in reach]
        if not cells:
            continue
        outlets = sorted({d for d, _, _ in cells})
        share = np.array([DEST_TYPE[next(t for x, _, t, *_ in dests if x == d)][2]
                          * rng.lognormal(0.0, DEST_SHARE_SD) for d in outlets])
        share /= share.sum()
        if len(outlets) >= 3:
            for _ in range(10):  # cap one outlet's share, redistribute the excess
                share = np.minimum(share, DEST_SHARE_CAP)
                share /= share.sum()
        share = dict(zip(outlets, share, strict=True))
        raw = {}
        for d in outlets:
            m = 1.0
            for day in range(days):
                m = 1 + DEMAND_AR[0] * (m - 1) + rng.normal(0, DEMAND_AR[1])
                if (d, day) in reach:
                    raw[(d, day)] = max(m, 0.1)
        n_days = {d: sum(1 for x, _ in raw if x == d) for d in outlets}
        total = float(supply.get(c, 0.0)) * rng.uniform(*DEMAND_SUPPLY_RATIO)
        for (d, day), m in sorted(raw.items()):
            p50 = _r(total * share[d] * m / n_days[d])
            rows.append((d, c, day, p50, _r(p50 * q10r), _r(p50 * q90r), ""))
    demand = pd.DataFrame(rows, columns=list(S.DEMAND)).sort_values(
        ["dest_id", "commodity", "day"], ignore_index=True)
    prices = pd.DataFrame(prow, columns=list(S.PRICES)).sort_values(
        ["dest_id", "commodity", "day"], ignore_index=True)

    dem_day = demand.groupby("dest_id").demand_kg_p50.sum() / days
    rows = []
    for d, nm, typ, *_ in dests:
        (wo, wc), _, _, head, hh, hc = DEST_TYPE[typ]
        rows.append((d, nm, typ, _r(float(dem_day.get(d, 0.0)) * head * rng.uniform(0.9, 1.1), 0),
                     hh, _r(hc * rng.uniform(0.9, 1.1)), wo, wc))
    destinations = pd.DataFrame(rows, columns=list(S.DESTINATIONS))
    events = pd.DataFrame(event_rows or [], columns=list(S.EVENTS))
    geo = pd.DataFrame([(h, "hub", nm, la, lo) for h, nm, la, lo in hubs]
                       + [(d, "destination", nm, la, lo) for d, nm, _, la, lo, _ in dests],
                       columns=list(S.GEO))

    for tname, df in [("commodities", commodities), ("batches", batches),
                      ("destinations", destinations), ("demand", demand), ("prices", prices),
                      ("lanes", lanes), ("vehicles", vehicles), ("events", events),
                      ("geo", geo)]:
        df.to_csv(out / f"{tname}.csv", index=False, lineterminator="\n")
    meta = {
        "schema_version": SCHEMA_VERSION, "name": name, "source": "synthetic", "seed": seed,
        "horizon_days": days, "window_mode": "daily", "dispatch_hour": DISPATCH_HOUR,
        "price_source": PRICE_SOURCE,
        "notes": f"SYNTHETIC data from freshroute.generator {GENERATOR_VERSION}. Real place "
                 "names and coordinates; quantities, demand, costs and prices are generated "
                 "(prices from a static table grounded on published Agmarknet aggregates, not "
                 "a snapshot). Not real.",
    }
    (out / "scenario.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return out


# name -> (seed, n_batches, n_dests, days, n_vehicles, event rows)
COMMITTED = {
    "practice": (42, 200, 8, 3, 6, None),
    "small": (42, 30, 3, 2, 2, None),
    # hidden-style suite: scale ladder, one scenario per event type, edge cases as data
    "hidden_small": (101, 30, 3, 2, 2, None),
    "hidden_practice": (102, 200, 8, 3, 4, None),
    "hidden_3x": (103, 600, 8, 3, 8, None),
    "hidden_10x": (104, 2000, 8, 3, 30, None),
    "hidden_ev_delay": (201, 200, 8, 3, 4, [("EV1", "route_delay", "HUB1|D1|reefer", 6.0, 8.0)]),
    "hidden_ev_capacity": (202, 200, 8, 3, 4, [("EV1", "capacity_drop", "vehicle:V1", 0.5, 8.0)]),
    "hidden_ev_demand": (203, 200, 8, 3, 4, [("EV1", "demand_spike", "dest:D2|*", 1.5, 8.0)]),
    "hidden_ev_price": (204, 200, 8, 3, 4, [("EV1", "price_shock", "dest:D3|tomato", 0.8, 8.0)]),
    "hidden_ev_order": (205, 200, 8, 3, 4, [("EV1", "new_order", "dest:D2|mango", 500.0, 8.0)]),
    "hidden_edge": (206, 30, 3, 2, 2, None),
}


def generate_committed(name: str, root: str | Path) -> Path:
    """Regenerate one committed scenario under `root` (normally data/scenarios)."""
    seed, nb, nd, days, nv, ev = COMMITTED[name]
    out = generate(name, seed, nb, nd, days, nv, Path(root) / name, event_rows=ev)
    if name == "hidden_edge":  # an already-expired batch and a vehicle with zero trips
        b = pd.read_csv(out / "batches.csv")
        b.loc[len(b)] = ["BEDGE01", "spinach", "HUB1", 200.0, 0.0, 0.0, 0.0, 20.0, "B", 0.0]
        b.to_csv(out / "batches.csv", index=False, lineterminator="\n")
        v = pd.read_csv(out / "vehicles.csv")
        v.loc[v.vehicle_id == "V1", "max_trips_day"] = 0
        v.to_csv(out / "vehicles.csv", index=False, lineterminator="\n")
    return out


if __name__ == "__main__":  # regenerate every committed scenario
    _root = Path(__file__).resolve().parents[3] / "data" / "scenarios"
    for _name in COMMITTED:
        generate_committed(_name, _root)
