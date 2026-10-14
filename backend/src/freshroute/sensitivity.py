"""One-at-a-time sensitivity harness (ARCHITECTURE.md section 14; DATABASE.md section 5.12).

Re-plans and re-simulates `milp_markdown` with one parameter moved at a time; everything else
stays at its scenario/config value. Perturbations are applied to an in-memory copy of the
scenario tables (q10, price_elasticity, demand) or passed as policy ctx (overship_slack);
values live in config.py. Rows at the base value reuse the base run.
"""
from __future__ import annotations

import copy
from pathlib import Path

import pandas as pd

from freshroute import metrics as M
from freshroute.config import (
    OVERSHIP_SLACK,
    SENS_DEMAND_MULT,
    SENS_ELASTICITY_MULT,
    SENS_OVERSHIP_SLACK,
    SENS_Q10,
)
from freshroute.io import Scenario, load_scenario
from freshroute.policies.milp import MilpMarkdownPolicy
from freshroute.simulator import simulate

POLICY = "milp_markdown"
COLUMNS = ("parameter", "value", "policy", "net_inr", "spoilage_kg", "demand_fulfillment_pct")
DEMAND_COLS = ["demand_kg_p10", "demand_kg_p50", "demand_kg_p90"]


def _kpis(sc: Scenario, ctx: dict) -> dict:
    res = MilpMarkdownPolicy().plan(sc, ctx)
    return M.compute(sc, res.plan, res.discounts, simulate(sc, res.plan, res.discounts))["kpis"]


def _with(sc: Scenario, table: str, cols: list[str], fn) -> Scenario:
    s = copy.deepcopy(sc)
    s.tables[table][cols] = fn(s.tables[table][cols])
    return s


def run_sensitivity(scenario: str, seed: int, out: str | None = None) -> Path:
    """Write <out or outputs/<name>__sensitivity__s<seed>>/sensitivity.csv; return the dir."""
    sc = load_scenario(scenario)
    ctx = {"seed": seed}
    base = _kpis(sc, ctx)
    cases = (
        [("q10", v, _with(sc, "commodities", ["q10"], lambda c, v=v: v), ctx) for v in SENS_Q10]
        + [("elasticity_multiplier", m,
            _with(sc, "commodities", ["price_elasticity"], lambda c, m=m: c * m), ctx)
           for m in SENS_ELASTICITY_MULT]
        + [("overship_slack", v, sc, {**ctx, "overship_slack": v}) for v in SENS_OVERSHIP_SLACK]
        + [("demand_multiplier", m, _with(sc, "demand", DEMAND_COLS, lambda d, m=m: d * m), ctx)
           for m in SENS_DEMAND_MULT]
    )
    is_base = {"elasticity_multiplier": 1.0, "demand_multiplier": 1.0,
               "overship_slack": OVERSHIP_SLACK}
    rows = []
    for param, value, s, c in cases:
        k = base if is_base.get(param) == value else _kpis(s, c)
        rows.append({"parameter": param, "value": value, "policy": POLICY,
                     **{col: k[col] for col in COLUMNS[3:]}})
    out_dir = Path(out) if out else Path("outputs") / f"{sc.name}__sensitivity__s{seed}"
    out_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows, columns=list(COLUMNS)).to_csv(out_dir / "sensitivity.csv", index=False)
    return out_dir
