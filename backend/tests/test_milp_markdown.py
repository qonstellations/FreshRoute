"""C-11: milp_markdown pipeline (plan -> discount.py -> discounts.csv -> simulator)."""
import json
from pathlib import Path

import pandas as pd
import pytest

from freshroute import cli
from freshroute.policies import milp

ROOT = Path(__file__).parents[2]
SCENARIOS = [ROOT / "backend" / "tests" / "fixtures" / "tiny_3batch",
             ROOT / "data" / "scenarios" / "practice"]


@pytest.mark.parametrize("path", SCENARIOS, ids=lambda p: p.name)
def test_milp_markdown_run(path, tmp_path, monkeypatch):
    monkeypatch.setattr(milp, "MILP_TIME_LIMIT_S", 10)  # practice hits the limit; keep CI quick
    out = cli.run(str(path), "milp_markdown", 42, str(tmp_path))
    m = json.loads((out / "metrics.json").read_text())
    man = json.loads((out / "run_manifest.json").read_text())
    val = json.loads((out / "validation.json").read_text())
    assert val["violation_total"] == 0, val  # includes DISCOUNT_* codes
    assert man["flags"]["markdown"] is True and man["policy"] == "milp_markdown"
    assert (pd.read_csv(out / "plan.csv").policy == "milp_markdown").all()
    assert m["kpis"]["violations"] == 0 and m["kpis"]["net_inr"] == m["economics_inr"]["net"]
    v = m["volumes_kg"]
    assert abs(v["total_supply"] - v["sold"] - m["kpis"]["spoilage_kg"]
               - v["carryover"]["total"]) < 1e-6
    disc = pd.read_csv(out / "discounts.csv")
    assert (disc.groupby("lot_id").discount_pct.diff().dropna() >= -1e-9).all()
