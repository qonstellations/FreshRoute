"""edge cases (AGENTS.md rule 6): each mutates a copy of tiny_3batch; every policy must
run end to end and produce a plan the validator accepts (violations == 0). fifo and
last_day_50 are naive by design (A-31: they ignore shelf life and windows, so they already
score 2 SHELF_LIFE violations on tiny_3batch itself); for them only those codes may appear."""
import json
import shutil
from pathlib import Path

import pandas as pd
import pytest

from freshroute.cli import POLICIES, run

FIXTURE = Path(__file__).parent / "fixtures" / "tiny_3batch"
NAIVE = ("fifo", "last_day_50")


def _zero_trips(d: Path) -> None:
    _edit(d, "vehicles", lambda v: v.assign(max_trips_day=0))


def _expired_batch(d: Path) -> None:
    def f(b):
        b.loc[b.batch_id == "B2", ["remaining_shelf_life_h", "rsl_p10_h", "rsl_p90_h"]] = 0
        return b
    _edit(d, "batches", f)


def _demand_spike(d: Path) -> None:
    def f(m):
        hit = (m.dest_id == "D1") & (m.commodity == "tomato") & (m.day == 1)
        m.loc[hit, ["demand_kg_p10", "demand_kg_p50", "demand_kg_p90"]] *= 10
        return m
    _edit(d, "demand", f)


def _no_demand_day(d: Path) -> None:
    _edit(d, "demand", lambda m: m[m.day != 1])


def _single_destination(d: Path) -> None:
    for t in ("destinations", "lanes", "demand", "prices"):
        _edit(d, t, lambda df: df[df.dest_id != "D2"])


def _edit(d: Path, table: str, fn) -> None:
    f = d / f"{table}.csv"
    fn(pd.read_csv(f)).to_csv(f, index=False)


CASES = {"zero_trips": _zero_trips, "expired_batch": _expired_batch,
         "demand_spike": _demand_spike, "no_demand_day": _no_demand_day,
         "single_destination": _single_destination}


@pytest.mark.parametrize("policy", POLICIES)
@pytest.mark.parametrize("case", sorted(CASES))
def test_edge_case_runs_and_validates(tmp_path, case, policy):
    sc = tmp_path / "sc"
    shutil.copytree(FIXTURE, sc, ignore=shutil.ignore_patterns("expected"))
    CASES[case](sc)
    out = run(str(sc), policy, 42, out=str(tmp_path / "out"))
    report = json.loads((out / "validation.json").read_text(encoding="utf-8"))
    if policy in NAIVE:  # ignore shelf life/windows by design; validator reports the cost
        assert set(report["counts"]) <= {"SHELF_LIFE", "WINDOW"}, report["counts"]
    else:
        assert report["violation_total"] == 0, report["counts"]
    if case == "zero_trips":
        assert pd.read_csv(out / "plan.csv").empty
