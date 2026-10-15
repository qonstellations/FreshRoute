"""Profit-vs-spoilage frontier (ARCHITECTURE.md section 14.6; DATABASE.md section 5.13).

Re-plans `milp` once per spoilage weight in FRONTIER_LAMBDAS (ctx `lambda_spoil`, A-53) and
scores every plan with the one simulator; the trade-off is measured, never computed here.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from freshroute.config import FRONTIER_LAMBDAS, FRONTIER_TIME_LIMIT_S
from freshroute.data.io import load_scenario
from freshroute.domain.discount import COLUMNS as DISCOUNT_COLUMNS
from freshroute.engine import metrics as M
from freshroute.engine.simulator import simulate
from freshroute.policies.milp import MilpPolicy
from freshroute.runs import naming

NO_DISCOUNTS = pd.DataFrame(columns=list(DISCOUNT_COLUMNS))
KPIS = ("net_inr", "spoilage_kg", "demand_fulfillment_pct", "min_dest_fill_pct")
COLUMNS = ("lambda_spoil", *KPIS)


def run_frontier(scenario: str, seed: int, out: str | None = None,
                 lambdas=FRONTIER_LAMBDAS, time_limit_s: float = FRONTIER_TIME_LIMIT_S) -> Path:
    """Write <out or outputs/<name>__frontier__s<seed>>/frontier.csv; return the dir."""
    sc = load_scenario(scenario)
    rows = []
    for lam in lambdas:
        res = MilpPolicy().plan(sc, {"seed": seed, "lambda_spoil": lam,
                                     "time_limit_s": time_limit_s})
        k = M.compute(sc, res.plan, NO_DISCOUNTS, simulate(sc, res.plan, NO_DISCOUNTS))["kpis"]
        rows.append({"lambda_spoil": lam, **{c: k[c] for c in KPIS}})
    out_dir = Path(out) if out else Path("outputs") / naming.run_id(sc.name, "frontier", seed)
    out_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows, columns=list(COLUMNS)).to_csv(out_dir / "frontier.csv", index=False)
    return out_dir
