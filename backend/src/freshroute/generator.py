"""Seeded synthetic scenario generator (ARCHITECTURE.md section on practice data;
DATABASE.md sections 3.1-3.10). SYNTHETIC: no organizer data, no Agmarknet snapshot
(PRE-02 missed), so prices come from the report-grounded static table below
(modal levels and volatility from published Agmarknet aggregates, not a snapshot).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from freshroute import schema as S
from freshroute.config import DISPATCH_HOUR, SCHEMA_VERSION

# [team] modal prices, INR/kg, from published Agmarknet aggregates (Farmer.in
# CC-BY ticker + CEDA series, July 2026; keyless, NOT a data.gov.in snapshot).
# Disclose in README. Volatility bands: onion is violently seasonal (18-67).
STATIC_PRICE_INR_KG = {
    "tomato": 28.0, "spinach": 35.0, "banana": 32.0, "mango": 70.0, "onion": 24.0, "potato": 18.0,
}
PRICE_SOURCE = "static_table_generator_v2"
PRICE_DAY_VOL = {  # per-day random-walk step per commodity
    "tomato": 0.08, "spinach": 0.10, "banana": 0.08, "mango": 0.10, "onion": 0.18, "potato": 0.12,
}
PRICE_SPREAD = {  # (min_ratio, max_ratio) per commodity; onion spreads wide
    "tomato": (0.90, 1.12), "spinach": (0.88, 1.15), "banana": (0.90, 1.12),
    "mango": (0.88, 1.15), "onion": (0.75, 1.30), "potato": (0.85, 1.20),
}
# [team] class, shelf h, ref C, q10, min_sell h, loss %, cost, disposal, salvage,
# elasticity, max discount %  (DATABASE.md 3.1 starting points; mango/potato are ours)
_COMM = {
    "tomato": ("very_high", 120, 20, 2.0, 24, 3.0, 15, 2, 3, 1.0, 35),
    "spinach": ("very_high", 60, 20, 2.0, 12, 4.0, 18, 2, 2, 1.2, 35),
    "banana": ("high", 150, 20, 2.0, 24, 2.0, 18, 2, 5, 0.8, 30),
    "mango": ("high", 120, 20, 2.0, 24, 3.0, 40, 3, 10, 0.8, 30),
    "onion": ("low", 720, 20, 2.0, 48, 1.0, 12, 1, 4, 0.5, 20),
    "potato": ("low", 900, 20, 2.0, 48, 1.0, 10, 1, 4, 0.5, 20),
}
# [team] commodity mix ~ NABCONS production shares (potato/onion heavy; spinach
# has no NABCONS row and stays a minor leafy line). Must sum to 1.
_COMM_W = {"tomato": 0.12, "spinach": 0.06, "banana": 0.22, "mango": 0.13,
           "onion": 0.18, "potato": 0.29}
# [team] RSL grade mix (A-47): grade A 70 % (0.75-1.0 of base), grade B 30 % (0.45-0.75).
RSL_GRADES = ((0.70, 0.75, 1.00), (0.30, 0.45, 0.75))
# [team] demand p10/p90 ratios per perishability class (low class is predictable).
_Q = {"very_high": (0.70, 1.35), "high": (0.75, 1.30), "low": (0.85, 1.15)}
DEMAND_DAY_VOL = 0.08  # per-day random-walk step on the demand multiplier
# [team] C-10/A-47 calibration knobs: tuned so naive FIFO lands in the A-47 bands.
QTY_KG = (80, 480)  # batch size range; was 300-1800 (supply ~3x fleet reach)
DEMAND_SUPPLY_RATIO = 1.2  # total p50 demand / supply per commodity
VEHICLE_CAP_KG = (2000, 3000, 4000)
RAIL_CAP_KG = 10000  # rail vehicle per hub so rail arcs are live (was: none)
MAX_TRIPS_DAY = 4  # ponytail: no trip-duration check; trips are fleet slots
RAIL_TRIPS_DAY = 2
_DEST_TYPES = ("mandi", "retail_DC", "HoReCa", "processor")
_BASE_LATLON = (12.97, 77.59)  # arbitrary synthetic anchor


def _r(x, n=2):
    return float(np.round(x, n))


def generate(name: str, seed: int, n_batches: int, n_dests: int, days: int,
             n_vehicles: int, out_dir: str | Path,
             event_rows: list[tuple] | None = None) -> Path:
    """Write a complete scenario folder to `out_dir` and return it.

    `event_rows` holds `(event_id, type, target, magnitude, at_h)` tuples for
    event-bearing (hidden-style) scenarios; otherwise `events.csv` is empty.
    """
    rng = np.random.default_rng(seed)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    comms = sorted(_COMM)
    w_mix = [(_COMM_W[c]) for c in comms]
    n_hubs = 2 if n_dests > 4 else 1
    hubs = [f"HUB{i + 1}" for i in range(n_hubs)]
    dest_ids = [f"D{i + 1}" for i in range(n_dests)]

    commodities = pd.DataFrame([(c, *_COMM[c]) for c in comms], columns=list(S.COMMODITIES))

    rows = []
    for i in range(n_batches):
        c = comms[rng.choice(len(comms), p=w_mix)]
        g = rng.random()
        for share, lo, hi in RSL_GRADES:
            if g < share:
                break
            g -= share
        rsl = _r(_COMM[c][1] * rng.uniform(lo, hi))
        rows.append((
            f"B{i + 1:04d}", c, hubs[rng.integers(n_hubs)], _r(rng.uniform(*QTY_KG)),
            rsl, _r(rsl * 0.85), _r(rsl * 1.15), float(rng.choice([15.0, 20.0, 25.0])),
            str(rng.choice(["A", "B"])), float(24 * rng.integers(0, max(days - 1, 1))),
        ))
    batches = pd.DataFrame(rows, columns=list(S.BATCHES))

    # demand sized so total p50 demand ~ DEMAND_SUPPLY_RATIO x supply per commodity;
    # dirichlet dest weights x per-(dest, commodity) day random walk (mean-preserving).
    supply = batches.groupby("commodity")["qty_kg"].sum()
    w = rng.dirichlet(np.ones(n_dests))
    rows, prow = [], []
    for c in comms:
        q10r, q90r = _Q[_COMM[c][0]]
        per_day = float(supply.get(c, 0.0)) * DEMAND_SUPPLY_RATIO / days
        for di, d in enumerate(dest_ids):
            base_p = STATIC_PRICE_INR_KG[c] * rng.uniform(0.85, 1.15)
            m = 1.0
            mult = []
            for _ in range(days):
                m *= rng.uniform(1 - DEMAND_DAY_VOL, 1 + DEMAND_DAY_VOL)
                mult.append(m)
            mean = sum(mult) / len(mult)
            p = base_p
            for day in range(days):
                p50 = _r(per_day * w[di] * mult[day] / mean * rng.uniform(0.9, 1.1))
                rows.append((d, c, day, p50, _r(p50 * q10r), _r(p50 * q90r), ""))
                p = _r(p * rng.uniform(1 - PRICE_DAY_VOL[c], 1 + PRICE_DAY_VOL[c]))
                smin, smax = PRICE_SPREAD[c]
                prow.append((d, c, day, p, _r(p * smin), _r(p * smax)))
    demand = pd.DataFrame(rows, columns=list(S.DEMAND))
    prices = pd.DataFrame(prow, columns=list(S.PRICES))

    # destinations: even index = full-horizon window; odd index = binding
    # sub-window (no last-day / no day-0 arrivals); caps tied to demand scale.
    dem_tot = demand.groupby("dest_id")["demand_kg_p50"].sum().to_dict()
    rows = []
    for i, d in enumerate(dest_ids):
        if i % 4 == 3:
            wo, wc = 24.0, float(24 * days)
        elif i % 2 == 1:
            wo, wc = 0.0, float(24 * (days - 1))
        else:
            wo, wc = 0.0, float(24 * days)
        cap = _r(dem_tot.get(d, 0.0) / days * rng.uniform(1.2, 2.0), 0)
        rows.append((d, f"Destination {i + 1}", _DEST_TYPES[i % 4],
                     cap, float(rng.choice([1.0, 2.0, 3.0])),
                     _r(rng.uniform(0.8, 2.0)), wo, wc))
    dests = pd.DataFrame(rows, columns=list(S.DESTINATIONS))

    # lanes: reefer + ambient hub->dest; one rail lane per hub to the first dest
    rows = []
    for h in hubs:
        for d in dest_ids:
            t = _r(rng.uniform(4, 20))
            fx = _r(rng.uniform(1500, 3000), 0)
            vr = _r(rng.uniform(1.5, 3.0))
            rows.append((h, d, "reefer", t, _r(t * 1.3), fx, vr, 10.0, ""))
            rows.append((h, d, "ambient", t, _r(t * 1.3), _r(fx * 0.5, 0), _r(vr * 0.6), 28.0, ""))
        rows.append((h, dest_ids[0], "rail", 30.0, 38.0, 1500.0, 0.8, 22.0, "18|22"))
    lanes = pd.DataFrame(rows, columns=list(S.LANES))
    lanes = lanes.sort_values(["origin", "dest_id", "mode"]).reset_index(drop=True)

    rows = []
    for i in range(n_vehicles):
        mode = "reefer" if i % 2 == 0 else "ambient"
        rows.append((f"V{i + 1}", hubs[i % n_hubs], mode,
                     float(rng.choice(VEHICLE_CAP_KG)), 0.0, MAX_TRIPS_DAY))
    for i, h in enumerate(hubs):
        rows.append((f"VR{i + 1}", h, "rail", float(RAIL_CAP_KG), 0.0, RAIL_TRIPS_DAY))
    vehicles = pd.DataFrame(rows, columns=list(S.VEHICLES))
    events = pd.DataFrame(event_rows or [], columns=list(S.EVENTS))

    lat0, lon0 = _BASE_LATLON
    nodes = [(h, "hub") for h in hubs] + [(d, "destination") for d in dest_ids]
    geo = pd.DataFrame(
        [(n, t, n, _r(lat0 + rng.uniform(-2, 2), 4), _r(lon0 + rng.uniform(-2, 2), 4))
         for n, t in nodes], columns=list(S.GEO))

    for tname, df in [("commodities", commodities), ("batches", batches),
                       ("destinations", dests), ("demand", demand), ("prices", prices),
                       ("lanes", lanes), ("vehicles", vehicles), ("events", events), ("geo", geo)]:
        df.to_csv(out / f"{tname}.csv", index=False, lineterminator="\n")
    meta = {
        "schema_version": SCHEMA_VERSION, "name": name, "source": "synthetic", "seed": seed,
        "horizon_days": days, "window_mode": "absolute", "dispatch_hour": DISPATCH_HOUR,
        "price_source": PRICE_SOURCE,
        "notes": "SYNTHETIC data from freshroute.generator v2. Prices are a static "
                 "table grounded on published Agmarknet aggregates, not a snapshot. "
                 "Not real.",
    }
    (out / "scenario.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return out


if __name__ == "__main__":  # regenerate committed scenarios
    generate("practice", 42, 200, 8, 3, 3, "data/scenarios/practice")
    generate("small", 42, 30, 3, 2, 2, "data/scenarios/small")
