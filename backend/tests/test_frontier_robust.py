"""frontier.csv (DATABASE.md section 5.13) and the milp_robust policy (ARCHITECTURE.md 14.5)."""
import json
from pathlib import Path

import pandas as pd

from freshroute import config
from freshroute.cli import main, run
from freshroute.data.io import load_scenario
from freshroute.domain.feasibility import build_arcs
from freshroute.policies.milp_robust import pessimistic
from freshroute.runs.frontier import mark_dominated

SCENARIO = str(Path(__file__).parent / "fixtures" / "tiny_3batch")
KEYS = ["batch_id", "dest_id", "vehicle_id", "dispatch_day"]


def test_frontier_csv(tmp_path):
    main(["frontier", "--scenario", SCENARIO, "--seed", "42", "--out", str(tmp_path / "f")])
    df = pd.read_csv(tmp_path / "f" / "frontier.csv")
    assert list(df.columns) == ["lambda_spoil", "net_inr", "spoilage_kg",
                                "demand_fulfillment_pct", "min_dest_fill_pct",
                                "spoilage_cost_inr", "dominated"]
    assert list(df.lambda_spoil) == list(config.FRONTIER_LAMBDAS)
    k = json.loads((run(SCENARIO, "milp", 42, out=str(tmp_path / "r"))
                    / "metrics.json").read_text(encoding="utf-8"))["kpis"]
    # lambda = 1 is warm-started from lambda = 0's plan; on this fixture both solve to optimum
    base = df[df.lambda_spoil == config.LAMBDA_SPOIL].iloc[0]
    for c in ("net_inr", "spoilage_kg", "demand_fulfillment_pct"):
        assert abs(base[c] - k[c]) <= config.FLOAT_TOL


def test_mark_dominated():
    df = pd.DataFrame({"net_inr": [10.0, 8.0, 12.0, 9.0], "spoilage_kg": [5.0, 3.0, 6.0, 6.0]})
    assert list(mark_dominated(df)) == [False, False, False, True]


def test_pessimistic_arcs_subset_of_base():
    sc = load_scenario(SCENARIO)
    base = build_arcs(sc)
    rob = build_arcs(pessimistic(sc))
    b = set(map(tuple, base[base.feasible][KEYS].values))
    r = set(map(tuple, rob[rob.feasible][KEYS].values))
    assert r <= b


def test_milp_robust_runs_clean(tmp_path):
    d = run(SCENARIO, "milp_robust", 42, out=str(tmp_path / "rb"))
    v = json.loads((d / "validation.json").read_text(encoding="utf-8"))
    m = json.loads((d / "metrics.json").read_text(encoding="utf-8"))
    assert m["policy"] == "milp_robust" and m["kpis"]["violations"] == 0
    assert v["violation_total"] == 0 if "violation_total" in v else True
