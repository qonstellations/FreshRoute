"""Scenario assembly (ARCHITECTURE.md section 5): generate() composes small builders that
draw from one seeded RNG in a fixed order (batches, lanes, fleet, demand + prices,
destinations); changing that order changes every committed scenario."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from freshroute import schema as S
from freshroute.config import DISPATCH_HOUR, HOURS_PER_DAY, SCHEMA_VERSION

from .constants import (
    _COMM,
    _COMM_W,
    _Q,
    COMMITTED,
    DEMAND_AR,
    DEMAND_SUPPLY_RATIO,
    DEST_SHARE_CAP,
    DEST_SHARE_SD,
    DEST_TYPE,
    DUTY_H,
    GENERATOR_VERSION,
    GRADE_A_MIN_FRAC,
    PRICE_DAY_VOL,
    PRICE_SOURCE,
    PRICE_SPREAD,
    QTY_CLIP_KG,
    QTY_LOGNORMAL,
    RAIL_CAP_KG,
    RAIL_TRIPS_DAY,
    RSL_BAND,
    RSL_BETA,
    STATIC_PRICE_INR_KG,
    STORAGE_TEMP_C,
    VEHICLE_CAP_KG,
    VEHICLE_CAP_P,
)
from .geography import DESTS, HUBS, _r, build_lanes, reachable


def build_commodities(comms) -> pd.DataFrame:
    return pd.DataFrame([(c, *_COMM[c]) for c in comms], columns=list(S.COMMODITIES))


def build_batches(rng, comms, hubs, n_batches: int, days: int) -> pd.DataFrame:
    """Remaining life ~ Beta share of base; grade follows from it; storage temp by
    commodity; availability spread over the horizon."""
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
    return pd.DataFrame(rows, columns=list(S.BATCHES))


def build_vehicles(rng, hubs, lanes, n_vehicles: int) -> pd.DataFrame:
    """Both road modes at every hub; trips/day from the hub's median road lane."""
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
    return pd.DataFrame(rows, columns=list(S.VEHICLES))


def build_demand_prices(rng, comms, dests, batches, reach, days: int):
    """Demand placed only on reachable (dest, day) cells, roughly matching supply; prices
    from the static table with a shared daily market move."""
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
    return demand, prices


def build_destinations(rng, dests, demand, days: int) -> pd.DataFrame:
    """Receiving capacity = headroom over mean daily demand; window and handling by type."""
    dem_day = demand.groupby("dest_id").demand_kg_p50.sum() / days
    rows = []
    for d, nm, typ, *_ in dests:
        (wo, wc), _, _, head, hh, hc = DEST_TYPE[typ]
        rows.append((d, nm, typ, _r(float(dem_day.get(d, 0.0)) * head * rng.uniform(0.9, 1.1), 0),
                     hh, _r(hc * rng.uniform(0.9, 1.1)), wo, wc))
    return pd.DataFrame(rows, columns=list(S.DESTINATIONS))


def build_geo(hubs, dests) -> pd.DataFrame:
    return pd.DataFrame([(h, "hub", nm, la, lo) for h, nm, la, lo in hubs]
                        + [(d, "destination", nm, la, lo) for d, nm, _, la, lo, _ in dests],
                        columns=list(S.GEO))


def scenario_meta(name: str, seed: int, days: int) -> dict:
    return {
        "schema_version": SCHEMA_VERSION, "name": name, "source": "synthetic", "seed": seed,
        "horizon_days": days, "window_mode": "daily", "dispatch_hour": DISPATCH_HOUR,
        "price_source": PRICE_SOURCE,
        "notes": f"SYNTHETIC data from freshroute.generator {GENERATOR_VERSION}. Real place "
                 "names and coordinates; quantities, demand, costs and prices are generated "
                 "(prices from a static table grounded on published Agmarknet aggregates, not "
                 "a snapshot). Not real.",
    }


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

    commodities = build_commodities(comms)
    batches = build_batches(rng, comms, hubs, n_batches, days)
    lanes = build_lanes(rng, hubs, dests)
    vehicles = build_vehicles(rng, hubs, lanes, n_vehicles)
    reach = reachable(lanes, vehicles, dests, days)
    demand, prices = build_demand_prices(rng, comms, dests, batches, reach, days)
    destinations = build_destinations(rng, dests, demand, days)
    events = pd.DataFrame(event_rows or [], columns=list(S.EVENTS))
    geo = build_geo(hubs, dests)

    for tname, df in [("commodities", commodities), ("batches", batches),
                      ("destinations", destinations), ("demand", demand), ("prices", prices),
                      ("lanes", lanes), ("vehicles", vehicles), ("events", events),
                      ("geo", geo)]:
        df.to_csv(out / f"{tname}.csv", index=False, lineterminator="\n")
    (out / "scenario.json").write_text(
        json.dumps(scenario_meta(name, seed, days), indent=2) + "\n", encoding="utf-8",
        newline="\n")
    return out


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
