"""Monte Carlo stress test (ARCHITECTURE.md section 14.1; DATABASE.md section 5.12).

The plan and the baseline are each solved once on the base scenario, then re-simulated (the one
simulator, never re-optimised) under the same sampled realizations: scenario i draws demand,
travel and RSL from numpy.random.default_rng(base_seed + i) (common random numbers, A-13, A-42).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from freshroute import metrics as M
from freshroute.config import (
    BASELINE,
    DEFAULT_SEED,
    FLOAT_TOL,
    MC_N,
    MC_NAMED,
    MC_TRAVEL_CAP_MULT,
    PLAN,
)
from freshroute.discount import COLUMNS as DISCOUNT_COLUMNS
from freshroute.io import Scenario, load_scenario
from freshroute.runs import naming
from freshroute.runs.runner import _policy
from freshroute.simulator import simulate

COLUMNS = ("scenario_i", "policy", "spoilage_kg", "spoilage_pct", "demand_fulfillment_pct",
           "min_dest_fill_pct", "net_inr")
BAND_KPIS = ("net_inr", "spoilage_kg", "demand_fulfillment_pct")


def inv_cdf(u, p10, p50, p90):
    """Piecewise-linear inverse CDF through (0.1, p10), (0.5, p50), (0.9, p90); the tails
    extend the end segments; clipped at 0 (ARCH 14.1)."""
    u, p10, p50, p90 = (np.asarray(x, dtype=float) for x in (u, p10, p50, p90))
    slope = np.where(u < 0.5, p50 - p10, p90 - p50) / 0.4
    return np.maximum(p50 + (u - 0.5) * slope, 0.0)


def travel_draw(u, p50, p90):
    """Delays only: p50 up to u = 0.5, then the p50->p90 line, capped at 1.5 x p90."""
    u, p50, p90 = (np.asarray(x, dtype=float) for x in (u, p50, p90))
    late = np.minimum(p50 + (u - 0.5) * (p90 - p50) / 0.4, MC_TRAVEL_CAP_MULT * p90)
    return np.where(u <= 0.5, p50, late)


def _tables(sc: Scenario):
    t = sc.tables
    return (t["demand"].sort_values(["dest_id", "commodity", "day"]),
            t["lanes"].sort_values(["origin", "dest_id", "mode"]),
            t["batches"].sort_values("batch_id"))


def realization(sc: Scenario, u_demand, u_travel, u_rsl) -> dict:
    """Simulator realization (A-28, A-42) from one uniform draw per demand row / lane / batch."""
    d, ln, b = _tables(sc)
    dem = inv_cdf(u_demand, d.demand_kg_p10, d.demand_kg_p50, d.demand_kg_p90)
    tr = travel_draw(u_travel, ln.travel_h_p50, ln.travel_h_p90)
    rsl = inv_cdf(u_rsl, b.rsl_p10_h, b.remaining_shelf_life_h, b.rsl_p90_h)
    return {
        "demand_kg": {(r.dest_id, r.commodity, int(r.day)): float(v)
                      for r, v in zip(d.itertuples(), dem, strict=True)},
        "travel_h": {(r.origin, r.dest_id, r.mode): float(v)
                     for r, v in zip(ln.itertuples(), tr, strict=True)},
        "rsl_h": {bid: float(v) for bid, v in zip(b.batch_id, rsl, strict=True)},
    }


def draws(sc: Scenario, n: int, seed: int, named: bool = False) -> list[tuple]:
    """Uniforms per scenario: seeded MC (rng(seed + i)) or the 3 named quantile sets."""
    sizes = [len(x) for x in _tables(sc)]
    if named:
        return [tuple(np.full(k, q) for k, q in zip(sizes, qs, strict=True))
                for qs in MC_NAMED.values()]
    out = []
    for i in range(n):
        rng = np.random.default_rng(seed + i)
        out.append(tuple(rng.random(k) for k in sizes))
    return out


def _solve(sc: Scenario, policy: str, seed: int):
    res = _policy(policy).plan(sc, {"seed": seed})
    disc = res.discounts if res.discounts is not None else pd.DataFrame(
        columns=list(DISCOUNT_COLUMNS))
    return res.plan, disc


def _band(x: np.ndarray) -> dict:
    p10, p50, p90 = np.percentile(x, [10, 50, 90])
    return {"p10": float(p10), "p50": float(p50), "p90": float(p90)}


def run_stress(scenario: str, policy: str = PLAN, n: int = MC_N, seed: int = DEFAULT_SEED,
               out: str | None = None, named: bool = False) -> Path:
    """Write stress.csv + stress_summary.json to <out or outputs/<name>__stress__s<seed>>."""
    sc = load_scenario(scenario)
    roles = (("plan", policy), ("baseline", BASELINE))
    solved = {role: _solve(sc, pol, seed) for role, pol in roles}
    rows, kp = [], {role: [] for role, _ in roles}
    for i, u in enumerate(draws(sc, n, seed, named)):
        real = realization(sc, *u)
        for role, pol in roles:
            plan, disc = solved[role]
            k = M.compute(sc, plan, disc, simulate(sc, plan, disc, real))["kpis"]
            kp[role].append(k)
            rows.append({"scenario_i": i, "policy": pol, **{c: k[c] for c in COLUMNS[2:]}})

    def col(role, c):
        return np.array([k[c] for k in kp[role]])
    summary = {
        "n": len(kp["plan"]), "base_seed": seed, "plan": policy, "baseline": BASELINE,
        "bands": {c: {role: _band(col(role, c)) for role, _ in roles} for c in BAND_KPIS},
        "share_plan_beats_baseline": {
            "net_inr": float(np.mean(col("plan", "net_inr") - col("baseline", "net_inr")
                                     > FLOAT_TOL)),
            "spoilage_kg": float(np.mean(col("baseline", "spoilage_kg")
                                         - col("plan", "spoilage_kg") > FLOAT_TOL)),
        },
    }
    out_dir = Path(out) if out else Path("outputs") / naming.run_id(sc.name, "stress", seed)
    out_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows, columns=list(COLUMNS)).to_csv(out_dir / "stress.csv", index=False)
    (out_dir / "stress_summary.json").write_text(json.dumps(summary, indent=2) + "\n",
                                                 encoding="utf-8")
    return out_dir
