"""Seeded synthetic scenario generator (ARCHITECTURE.md section on practice data;
DATABASE.md sections 3.1-3.10). SYNTHETIC: no organizer data, no Agmarknet snapshot
(PRE-02 missed), so prices come from the static table below.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from freshroute import schema as S
from freshroute.config import DISPATCH_HOUR, SCHEMA_VERSION

# [team] static modal prices, INR/kg, NOT Agmarknet data. Disclose in README.
STATIC_PRICE_INR_KG = {
    "tomato": 28.0, "spinach": 35.0, "banana": 32.0, "mango": 70.0, "onion": 24.0, "potato": 20.0,
}
PRICE_SOURCE = "static_table_generator_v1"
# [team] class, shelf h, ref C, q10, min_sell h, loss %, cost, disposal, salvage,
# elasticity, max discount %  (DATABASE.md 3.1 starting points; mango/potato are ours)
_COMM = {
    "tomato": ("very_high", 120, 20, 2.0, 24, 2.5, 15, 2, 3, 1.0, 35),
    "spinach": ("very_high", 60, 20, 2.0, 12, 4.0, 18, 2, 2, 1.2, 35),
    "banana": ("high", 150, 20, 2.0, 24, 2.0, 18, 2, 5, 0.8, 30),
    "mango": ("high", 120, 20, 2.0, 24, 3.0, 40, 3, 10, 0.8, 30),
    "onion": ("low", 720, 20, 2.0, 48, 1.0, 12, 1, 4, 0.5, 20),
    "potato": ("low", 900, 20, 2.0, 48, 1.0, 10, 1, 4, 0.5, 20),
}
_DEST_TYPES = ("mandi", "retail_DC", "HoReCa", "processor")
_BASE_LATLON = (12.97, 77.59)  # arbitrary synthetic anchor


def _r(x, n=2):
    return float(np.round(x, n))


def generate(name: str, seed: int, n_batches: int, n_dests: int, days: int,
             n_vehicles: int, out_dir: str | Path) -> Path:
    """Write a complete scenario folder to `out_dir` and return it."""
    rng = np.random.default_rng(seed)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    comms = sorted(_COMM)
    n_hubs = 2 if n_dests > 4 else 1
    hubs = [f"HUB{i + 1}" for i in range(n_hubs)]
    dest_ids = [f"D{i + 1}" for i in range(n_dests)]

    commodities = pd.DataFrame([(c, *_COMM[c]) for c in comms], columns=list(S.COMMODITIES))

    rows = []
    for i in range(n_batches):
        c = comms[rng.integers(len(comms))]
        rsl = _r(_COMM[c][1] * rng.uniform(0.4, 1.0))
        rows.append((
            f"B{i + 1:04d}", c, hubs[rng.integers(n_hubs)], _r(rng.uniform(300, 1800)),
            rsl, _r(rsl * 0.85), _r(rsl * 1.15), float(rng.choice([15.0, 20.0, 25.0])),
            str(rng.choice(["A", "B"])), float(24 * rng.integers(0, max(days - 1, 1))),
        ))
    batches = pd.DataFrame(rows, columns=list(S.BATCHES))

    rows = []
    for i, d in enumerate(dest_ids):
        rows.append((d, f"Destination {i + 1}", _DEST_TYPES[i % 4],
                     _r(rng.uniform(2500, 6000), 0), float(rng.choice([1.0, 2.0, 3.0])),
                     _r(rng.uniform(0.8, 2.0)), 0.0, float(24 * days)))
    dests = pd.DataFrame(rows, columns=list(S.DESTINATIONS))

    # demand sized so total p50 demand ~ 1.2 x supply per commodity
    supply = batches.groupby("commodity")["qty_kg"].sum()
    w = rng.dirichlet(np.ones(n_dests))
    rows, prow = [], []
    for c in comms:
        per_day = float(supply.get(c, 0.0)) * 1.2 / days
        for di, d in enumerate(dest_ids):
            base_p = STATIC_PRICE_INR_KG[c] * rng.uniform(0.9, 1.15)
            for day in range(days):
                p50 = _r(per_day * w[di] * rng.uniform(0.8, 1.2))
                rows.append((d, c, day, p50, _r(p50 * 0.75), _r(p50 * 1.3), ""))
                p = _r(base_p * rng.uniform(0.95, 1.05))
                prow.append((d, c, day, p, _r(p * 0.9), _r(p * 1.12)))
    demand = pd.DataFrame(rows, columns=list(S.DEMAND))
    prices = pd.DataFrame(prow, columns=list(S.PRICES))

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
                     float(rng.choice([2000, 3000, 4000])), 0.0, 2))
    vehicles = pd.DataFrame(rows, columns=list(S.VEHICLES))
    events = pd.DataFrame(columns=list(S.EVENTS))

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
        "notes": "SYNTHETIC data from freshroute.generator. Prices are a static table, "
                 "not Agmarknet. Not real.",
    }
    (out / "scenario.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return out


if __name__ == "__main__":  # regenerate committed scenarios
    generate("practice", 42, 200, 8, 3, 3, "data/scenarios/practice")
    generate("small", 42, 30, 3, 2, 2, "data/scenarios/small")
