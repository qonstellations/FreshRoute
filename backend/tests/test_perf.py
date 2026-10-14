"""smoke: perf harness runs at scale 1 on a tiny generated base scenario."""
import json

from freshroute.generator import generate
from freshroute.runs import perf


def test_perf_smoke(tmp_path):
    base = generate("tiny", 7, 10, 3, 2, 2, tmp_path / "base")
    res = perf.run(scale=1, seed=42, out=str(tmp_path / "out"), base=str(base))
    assert res["n_batches"] == 10 and res["arcs_total"] >= res["arcs_feasible"] > 0
    assert json.loads((tmp_path / "out" / "perf.json").read_text()) == res
