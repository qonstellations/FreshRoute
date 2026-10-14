"""F-08: generator output loads, is deterministic, and is keyed consistently."""
import json
from pathlib import Path

import pandas as pd
import pytest

from freshroute import cli
from freshroute import schema as S
from freshroute.generator import generate
from freshroute.io import load_scenario


@pytest.fixture
def sc(tmp_path):
    return load_scenario(generate("t", 7, 60, 5, 3, 3, tmp_path / "a"))


def test_loads_and_shapes(sc):
    t = sc.tables
    assert len(t["batches"]) == 60 and len(t["destinations"]) == 5 and len(t["vehicles"]) == 3
    assert len(t["demand"]) == 6 * 5 * 3 == len(t["prices"])
    assert sc.meta["source"] == "synthetic" and "price_source" in sc.meta


def test_pk_unique_and_fk(sc):
    for name, df in sc.tables.items():
        assert not df.duplicated(list(S.PKS[name])).any(), name
    for tab, col, ptab, pcol in S.FKS:
        assert sc.tables[tab][col].isin(sc.tables[ptab][pcol]).all()
    assert not [w for w in sc.warnings if "synthetic" not in w]


def test_deterministic(tmp_path):
    a = generate("t", 7, 60, 5, 3, 3, tmp_path / "a")
    b = generate("t", 7, 60, 5, 3, 3, tmp_path / "b")
    for f in a.iterdir():
        assert f.read_bytes() == (b / f.name).read_bytes(), f.name
    c = generate("t", 8, 60, 5, 3, 3, tmp_path / "c")
    assert (a / "batches.csv").read_bytes() != (c / "batches.csv").read_bytes()


def test_practice_fifo_calibrated(tmp_path):
    """C-10 / A-21: committed practice = generator output; naive FIFO near NABCONS spoilage."""
    practice = Path(__file__).parents[2] / "data" / "scenarios" / "practice"
    fresh = generate("practice", 42, 200, 8, 3, 3, tmp_path / "p")
    for f in sorted(practice.glob("*.csv")):
        pd.testing.assert_frame_equal(pd.read_csv(f), pd.read_csv(fresh / f.name))
    out = cli.run(str(practice), "fifo", 42, str(tmp_path / "run"))
    pc = {c["commodity"]: c["spoilage_pct"]
          for c in json.loads((out / "metrics.json").read_text())["per_commodity"]}
    assert abs(pc["tomato"] - 3.25) <= 1.5 and abs(pc["onion"] - 1.96) <= 1.5, pc
    assert max(pc.values()) < 10, pc
