"""Behaviour lock for refactors: sha256 of every run output vs hashes captured earlier.
Regenerate deliberately with GOLDEN_WRITE=1 (only when an output change is intended)."""
import hashlib
import json
import os
from pathlib import Path

import pytest

from freshroute.cli import run
from freshroute.config import MIP_REL_GAP

HERE = Path(__file__).parent
HASHES = HERE / "golden" / "hashes.json"
TINY = str(HERE / "fixtures" / "tiny_3batch")
PRACTICE = str(HERE.parents[1] / "data" / "scenarios" / "practice")
FILES = ("metrics.json", "plan.csv", "trips.csv", "discounts.csv", "sim_ledger.csv",
         "sim_lots.csv", "reason_cards.json", "dispatch_sheet.csv", "dispatch_sheet.txt",
         "validation.json")
# milp on practice hits its time limit, so it is not byte-reproducible and is not locked here
CASES = [(TINY, p) for p in ("fifo", "fefo", "last_day_50", "milp")] + \
        [(PRACTICE, p) for p in ("fifo", "fefo", "last_day_50")]
# milp on tiny stops at MIP_REL_GAP, so which near-optimal plan comes out differs between machines
# (solver build / CPU). There we lock what the gap guarantees instead of the plan's bytes:
# these outputs are identical for any near-optimal plan, plus net profit within the gap.
MILP_STABLE = ("discounts.csv", "dispatch_sheet.txt", "validation.json")


def _hashes(d: Path, files=FILES) -> dict:
    # normalise line endings so hashes match on Windows (CRLF) and Unix (LF)
    return {f: hashlib.sha256((d / f).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
            for f in files}


def _milp_golden(d: Path) -> dict:
    net = json.loads((d / "metrics.json").read_text(encoding="utf-8"))["kpis"]["net_inr"]
    return {**_hashes(d, MILP_STABLE), "net_inr": net}


def _check_milp(got: dict, stored: dict, key: str) -> None:
    rest = lambda g: {k: v for k, v in g.items() if k != "net_inr"}  # noqa: E731
    assert rest(got) == rest(stored), key
    # two plans each within MIP_REL_GAP of the optimum differ by at most about 2 * gap
    tol = 2 * MIP_REL_GAP * abs(stored["net_inr"])
    assert abs(got["net_inr"] - stored["net_inr"]) <= tol, (key, got["net_inr"], stored["net_inr"])


@pytest.mark.parametrize("scenario,policy", CASES, ids=[f"{Path(s).name}-{p}" for s, p in CASES])
def test_outputs_match_golden(tmp_path, scenario, policy):
    key = f"{Path(scenario).name}/{policy}"
    out = run(scenario, policy, 42, out=str(tmp_path))
    milp = policy == "milp"
    got = _milp_golden(out) if milp else _hashes(out)
    stored = json.loads(HASHES.read_text(encoding="utf-8")) if HASHES.exists() else {}
    if os.environ.get("GOLDEN_WRITE"):
        stored[key] = got
        HASHES.write_text(json.dumps(stored, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    if milp:
        _check_milp(got, stored[key], key)
    else:
        assert stored.get(key) == got, key
