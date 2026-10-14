"""Behaviour lock for refactors: sha256 of every run output vs hashes captured earlier.
Regenerate deliberately with GOLDEN_WRITE=1 (only when an output change is intended)."""
import hashlib
import json
import os
from pathlib import Path

import pytest

from freshroute.cli import run

HERE = Path(__file__).parent
HASHES = HERE / "golden" / "hashes.json"
TINY = str(HERE / "fixtures" / "tiny_3batch")
PRACTICE = str(HERE.parents[1] / "data" / "scenarios" / "practice")
FILES = ("metrics.json", "plan.csv", "trips.csv", "discounts.csv", "sim_ledger.csv",
         "sim_lots.csv", "reason_cards.json", "dispatch_sheet.csv", "dispatch_sheet.txt",
         "validation.json")
# milp on practice hits its time limit, so it is not byte-reproducible and is not locked here
CASES = [(TINY, p) for p in ("fifo", "fefo", "last_day_50", "milp", "milp_markdown")] + \
        [(PRACTICE, p) for p in ("fifo", "fefo", "last_day_50")]


def _hashes(d: Path) -> dict:
    return {f: hashlib.sha256((d / f).read_bytes()).hexdigest() for f in FILES}


@pytest.mark.parametrize("scenario,policy", CASES, ids=lambda x: Path(x).name if "/" in str(x) or "\\" in str(x) else x)
def test_outputs_match_golden(tmp_path, scenario, policy):
    key = f"{Path(scenario).name}/{policy}"
    got = _hashes(run(scenario, policy, 42, out=str(tmp_path)))
    stored = json.loads(HASHES.read_text(encoding="utf-8")) if HASHES.exists() else {}
    if os.environ.get("GOLDEN_WRITE"):
        stored[key] = got
        HASHES.write_text(json.dumps(stored, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    assert stored.get(key) == got, key
