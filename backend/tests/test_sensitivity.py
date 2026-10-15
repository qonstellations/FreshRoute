"""sensitivity.csv (DATABASE.md section 5.12) on tiny_3batch."""
import json
from pathlib import Path

import pandas as pd

from freshroute import config
from freshroute.cli import main, run

SCENARIO = str(Path(__file__).parent / "fixtures" / "tiny_3batch")


def test_sensitivity_csv(tmp_path):
    main(["sensitivity", "--scenario", SCENARIO, "--seed", "42", "--out", str(tmp_path / "s")])
    df = pd.read_csv(tmp_path / "s" / "sensitivity.csv")
    assert list(df.columns) == ["parameter", "value", "policy", "net_inr", "spoilage_kg",
                                "demand_fulfillment_pct"]
    n = (len(config.SENS_Q10) + len(config.SENS_ELASTICITY_MULT)
         + len(config.SENS_OVERSHIP_SLACK) + len(config.SENS_DEMAND_MULT))
    assert len(df) == n and not df.duplicated(["parameter", "value"]).any()
    assert set(df.policy) == {"milp"}
    k = json.loads((run(SCENARIO, "milp", 42, out=str(tmp_path / "r"))
                    / "metrics.json").read_text(encoding="utf-8"))["kpis"]
    base = df[(df.parameter == "demand_multiplier") & (df.value == 1.0)].iloc[0]
    for c in ("net_inr", "spoilage_kg", "demand_fulfillment_pct"):
        assert abs(base[c] - k[c]) <= config.FLOAT_TOL
