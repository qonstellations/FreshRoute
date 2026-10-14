"""Generator network (ARCHITECTURE.md section 5, A-49): hubs, destinations, great-circle
distance, lanes and the (destination, day) reachability map."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from freshroute.config import DISPATCH_HOUR, HOURS_PER_DAY
from freshroute.data import schema as S

from .constants import (
    DEST_TYPE,
    LANE_COST,
    LANE_COST_NOISE,
    RAIL_DWELL_H,
    RAIL_FACTOR,
    RAIL_MIN_KM,
    RAIL_SLOTS,
    RAIL_SPEED_KMH,
    ROAD_FACTOR,
    ROAD_LOAD_H,
    ROAD_SPEED_KMH,
    TRANSIT_TEMP_C,
    TRAVEL_P90_RATIO,
)

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



def build_lanes(rng, hubs, dests) -> pd.DataFrame:
    """Reefer + ambient from every hub; rail to far destinations."""
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
    return lanes.sort_values(["origin", "dest_id", "mode"]).reset_index(drop=True)


def reachable(lanes, vehicles, dests, days: int) -> set:
    """(dest, day) cells where some lane with a vehicle arrives inside the daily window."""
    fleet = set(zip(vehicles.origin, vehicles["mode"], strict=True))
    reach: set = set()
    for ln in lanes.to_dict("records"):
        if (ln["origin"], ln["mode"]) not in fleet:
            continue
        lo, hi = DEST_TYPE[next(t for d, _, t, *_ in dests if d == ln["dest_id"])][0]
        for a in _arrivals(ln, days):
            if a // HOURS_PER_DAY < days and lo <= a % HOURS_PER_DAY <= hi:
                reach.add((ln["dest_id"], int(a // HOURS_PER_DAY)))
    return reach
