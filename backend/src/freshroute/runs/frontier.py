"""Profit-vs-spoilage frontier (ARCHITECTURE.md section 14.6; DATABASE.md section 5.12).

Re-plans `milp` once per spoilage weight in FRONTIER_LAMBDAS (ctx `lambda_spoil`, A-53) and
scores every plan with the one simulator; the trade-off is measured, never computed here.
Each solve is warm-started from the previous weight's plan, and a point another point beats
on both net and spoilage kg is flagged `dominated` (a time-limited incumbent, not a trade-off).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from freshroute.config import FLOAT_TOL, FRONTIER_LAMBDAS, FRONTIER_TIME_LIMIT_S
from freshroute.data.io import load_scenario
from freshroute.domain.discount import COLUMNS as DISCOUNT_COLUMNS
from freshroute.engine import metrics as M
from freshroute.engine.simulator import simulate
from freshroute.policies.milp import MilpPolicy
from freshroute.runs import naming

NO_DISCOUNTS = pd.DataFrame(columns=list(DISCOUNT_COLUMNS))
KPIS = ("net_inr", "spoilage_kg", "demand_fulfillment_pct", "min_dest_fill_pct")
COLUMNS = ("lambda_spoil", *KPIS, "spoilage_cost_inr", "dominated")


def mark_dominated(df: pd.DataFrame) -> pd.Series:
    """True where another row has net >= and spoilage <=, one of them strictly (beyond tol)."""
    n, s = df.net_inr.to_numpy(), df.spoilage_kg.to_numpy()
    return pd.Series([any(
        n[j] >= n[i] - FLOAT_TOL and s[j] <= s[i] + FLOAT_TOL
        and (n[j] > n[i] + FLOAT_TOL or s[j] < s[i] - FLOAT_TOL)
        for j in range(len(df)) if j != i) for i in range(len(df))], index=df.index)


def run_frontier(scenario: str, seed: int, out: str | None = None,
                 lambdas=FRONTIER_LAMBDAS, time_limit_s: float = FRONTIER_TIME_LIMIT_S) -> Path:
    """Write <out or outputs/<name>__frontier__s<seed>>/frontier.csv; return the dir."""
    sc = load_scenario(scenario)
    rows, warm = [], None
    for lam in lambdas:
        ctx = {"seed": seed, "lambda_spoil": lam, "time_limit_s": time_limit_s}
        if warm is not None:
            ctx["warm_start"] = warm
        res = MilpPolicy().plan(sc, ctx)
        m = M.compute(sc, res.plan, NO_DISCOUNTS, simulate(sc, res.plan, NO_DISCOUNTS))
        rows.append({"lambda_spoil": lam, **{c: m["kpis"][c] for c in KPIS},
                     "spoilage_cost_inr": m["economics_inr"]["spoilage_cost"]})
        warm = res.plan
    df = pd.DataFrame(rows)
    df["dominated"] = mark_dominated(df) if len(df) else pd.Series(dtype=bool)
    out_dir = Path(out) if out else Path("outputs") / naming.run_id(sc.name, "frontier", seed)
    out_dir.mkdir(parents=True, exist_ok=True)
    df.reindex(columns=list(COLUMNS)).to_csv(out_dir / "frontier.csv", index=False)
    return out_dir
