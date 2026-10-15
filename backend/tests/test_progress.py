"""Show-while-solving (ARCHITECTURE.md section 16.2): progressive runs end on the same files
as a plain run, and report monotone versions with a single final one."""
import json
from pathlib import Path

from freshroute.cli import run
from freshroute.runs.progress import Progressive

TINY = str(Path(__file__).parent / "fixtures" / "tiny_3batch")


def test_progressive_run_matches_plain_run(tmp_path):
    events = []
    a = run(TINY, "milp", 42, str(tmp_path / "a"), on_progress=events.append)
    b = run(TINY, "milp", 42, str(tmp_path / "b"))
    assert events and events[-1]["final"] and not any(e["final"] for e in events[:-1])
    assert [e["version"] for e in events] == list(range(1, len(events) + 1))
    for f in ("metrics.json", "plan.csv", "trips.csv", "validation.json"):
        assert (a / f).read_bytes() == (b / f).read_bytes()
    assert json.loads((a / "metrics.json").read_text())["kpis"]["net_inr"] == events[-1]["net_inr"]
    assert not list(a.glob("*.tmp"))


def test_non_milp_policy_ignores_progress(tmp_path):
    events = []
    run(TINY, "fefo", 42, str(tmp_path), on_progress=events.append)
    assert events == []


class _B:
    def __init__(self, net):
        self.net_inr = net


def test_only_better_plans_are_published():
    got = []
    p = Progressive(lambda r: _B(r), got.append, lambda e: None)
    for profit, net in ((10, 5), (9, 99), (20, 5), (30, 7)):  # 2nd: lower profit, never offered
        p.offer(lambda net=net: net, profit)
        while p._slot is not None:  # let the worker take it before the next offer
            pass
    p.close()
    assert [b.net_inr for b in got][0] == 5 and all(b.net_inr > 5 for b in got[1:])
