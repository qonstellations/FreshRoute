"""same scenario + policy + seed => identical outputs (ARCHITECTURE.md section 18,
DATABASE.md section 5.1: only `timestamp_utc` and `solver.solve_seconds` may differ)."""
import json
from pathlib import Path

import pytest

from freshroute.cli import run

SCENARIO = str(Path(__file__).parent / "fixtures" / "tiny_3batch")
FILES = ("metrics.json", "plan.csv", "trips.csv", "discounts.csv", "sim_ledger.csv")


def _manifest(d):
    m = json.loads((d / "run_manifest.json").read_text(encoding="utf-8"))
    m.pop("timestamp_utc")
    if m.get("solver"):
        m["solver"].pop("solve_seconds", None)
    return m


@pytest.mark.parametrize("policy", ["fifo", "milp"])
def test_two_runs_identical(tmp_path, policy):
    a = run(SCENARIO, policy, 42, out=str(tmp_path / "a"))
    b = run(SCENARIO, policy, 42, out=str(tmp_path / "b"))
    for f in FILES:
        assert (a / f).read_bytes() == (b / f).read_bytes(), f
    assert _manifest(a) == _manifest(b)
