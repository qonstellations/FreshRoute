"""C-04 (ARCHITECTURE.md section 9.2): with overship 0, markdown off and the base realization,
the simulator's net_inr of the MILP plan equals the MILP objective without tie-break/slack."""
from pathlib import Path

import pandas as pd
import pytest

from freshroute import metrics
from freshroute.discount import COLUMNS
from freshroute.io import load_scenario
from freshroute.policies import milp
from freshroute.simulator import simulate

ROOT = Path(__file__).parents[2]


@pytest.mark.parametrize("path", [ROOT / "backend" / "tests" / "fixtures" / "tiny_3batch",
                                  ROOT / "data" / "scenarios" / "small"])
def test_milp_objective_equals_sim_net(path, monkeypatch):
    monkeypatch.setattr(milp, "OVERSHIP_SLACK", 0.0)
    s = load_scenario(path)
    plan = milp.MilpPolicy().plan(s)
    assert plan.solver["fallback_used"] is False
    disc = pd.DataFrame(columns=list(COLUMNS))  # markdown off
    net = metrics.compute(s, plan.plan, disc, simulate(s, plan.plan, disc))["kpis"]["net_inr"]
    # INR 0.01 per shipment line: float sums over lines, no modelling slack
    assert abs(net - plan.solver["objective_inr"]) <= 0.01 * max(len(plan.plan), 1)
