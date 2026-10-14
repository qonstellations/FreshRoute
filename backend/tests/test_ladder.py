"""Attribution ladder + waterfall reconciliation, and the MILP-beats-FEFO guard."""
import json
from pathlib import Path

import pytest

from freshroute import cli, generator, ladder
from freshroute.policies import milp

ROOT = Path(__file__).parents[2]
TINY = str(ROOT / "backend" / "tests" / "fixtures" / "tiny_3batch")


@pytest.fixture(scope="module")
def tiny_ladder(tmp_path_factory):
    out = tmp_path_factory.mktemp("ladder")
    lad_dir = ladder.run_ladder(TINY, 42, str(out))
    load = lambda p: json.loads(p.read_text(encoding="utf-8"))  # noqa: E731
    return out, load(lad_dir / "ladder.json"), load(lad_dir / "waterfall.json"), load


def test_waterfall_reconciles(tiny_ladder):
    out, _, wf, load = tiny_ladder
    steps = wf["steps"]
    assert [s["type"] for s in steps] == ["total"] + ["delta"] * 6 + ["total"]
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
    # 60-batch 3-day proxy: 30-batch 2-day instances admit greedy-optimal
    # solutions (FEFO ties MILP exactly), so they cannot guard the gate; 60-batch
    # instances have real allocation tension at ratio 1.5.
    monkeypatch.setattr(milp, "MILP_TIME_LIMIT_S", 10)
    sc = generator.generate("g2", seed, 60, 5, 3, 3, tmp_path / "sc")
    return {p: json.loads((cli.run(str(sc), p, seed, str(tmp_path / p)) / "metrics.json")
                          .read_text(encoding="utf-8"))["kpis"]
            for p in ("fefo", "milp", "milp_markdown")}


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_g2_net_and_violations(seed, tmp_path, monkeypatch):
    k = _g2_kpis(seed, tmp_path, monkeypatch)
    assert k["milp"]["net_inr"] > k["fefo"]["net_inr"]
    assert k["milp"]["violations"] == 0 and k["milp_markdown"]["violations"] == 0


def test_demo_writes_pitch_files(tmp_path, capsys):
    """`freshroute demo` writes every ladder run + ladder/waterfall and exits 0."""
    cli.main(["demo", "--scenario", TINY, "--seed", "42", "--out", str(tmp_path)])
    for pol in ladder.LADDER + ladder.EXTRAS:
        for f in ("metrics.json", "validation.json", "plan.csv", "reason_cards.json"):
            assert (tmp_path / f"tiny_3batch__{pol}__s42" / f).is_file()
    assert (tmp_path / "tiny_3batch__ladder__s42" / "ladder.json").is_file()
    assert (tmp_path / "tiny_3batch__ladder__s42" / "waterfall.json").is_file()
    out = capsys.readouterr().out
    assert "milp_markdown validation: 0 violation(s)" in out and "s wall" in out
