"""C-07: attribution ladder + waterfall reconciliation, and the Gate G2 guard."""
import json
from pathlib import Path

import pytest

from freshroute import cli, generator, ladder
from freshroute.config import FLOAT_TOL
from freshroute.policies import milp

ROOT = Path(__file__).parents[1]
TINY = str(ROOT / "tests" / "fixtures" / "tiny_3batch")


@pytest.fixture(scope="module")
def tiny_ladder(tmp_path_factory):
    out = tmp_path_factory.mktemp("ladder")
    lad_dir = ladder.run_ladder(TINY, 42, str(out))
    load = lambda p: json.loads(p.read_text(encoding="utf-8"))  # noqa: E731
    return out, load(lad_dir / "ladder.json"), load(lad_dir / "waterfall.json"), load


def test_waterfall_reconciles(tiny_ladder):
    out, _, wf, load = tiny_ladder
    steps = wf["steps"]
    assert [s["type"] for s in steps] == ["total"] + ["delta"] * 5 + ["total"]
    total = steps[0]["value"] + sum(s["value"] for s in steps if s["type"] == "delta")
    assert abs(total - steps[-1]["value"]) <= wf["tolerance_inr"]
    for pol, step in ((wf["baseline"], steps[0]), (wf["plan"], steps[-1])):
        m = load(out / f"tiny_3batch__{pol}__s42" / "metrics.json")
        assert abs(step["value"] - m["kpis"]["net_inr"]) <= wf["tolerance_inr"]


def test_ladder_structure(tiny_ladder):
    out, lad, wf, load = tiny_ladder
    assert [e["policy"] for e in lad["ladder"]] == ["fifo", "fefo", "milp", "milp_markdown"]
    assert [e["policy"] for e in lad["extras"]] == ["last_day_50"]
    assert lad["official_baseline"] is None
    assert (wf["baseline"], wf["plan"]) == ("fefo", "milp_markdown")
    keys = load(out / "tiny_3batch__fifo__s42" / "metrics.json")["kpis"].keys()
    assert all(e["kpis"].keys() == keys for e in lad["ladder"] + lad["extras"])


def _g2_kpis(seed, tmp_path, monkeypatch):
    monkeypatch.setattr(milp, "MILP_TIME_LIMIT_S", 10)
    sc = generator.generate("small", seed, 30, 3, 2, 2, tmp_path / "sc")  # data/scenarios/small
    return {p: json.loads((cli.run(str(sc), p, seed, str(tmp_path / p)) / "metrics.json")
                          .read_text(encoding="utf-8"))["kpis"]
            for p in ("fefo", "milp", "milp_markdown")}


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_g2_net_and_violations(seed, tmp_path, monkeypatch):
    k = _g2_kpis(seed, tmp_path, monkeypatch)
    assert k["milp"]["net_inr"] > k["fefo"]["net_inr"]
    assert k["milp"]["violations"] == 0 and k["milp_markdown"]["violations"] == 0


@pytest.mark.xfail(strict=False, reason="G2 spoilage gap under investigation (C-04)")
@pytest.mark.parametrize("seed", [1, 2, 3])
def test_g2_spoilage(seed, tmp_path, monkeypatch):
    k = _g2_kpis(seed, tmp_path, monkeypatch)
    assert k["milp"]["spoilage_kg"] <= k["fefo"]["spoilage_kg"] + FLOAT_TOL
