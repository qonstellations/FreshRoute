"""F-08: generator output loads, is deterministic, and is keyed consistently.
S-01f: A-47 calibration bands, hidden-suite integrity, rail fleet, binding windows.
"""
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
    assert len(t["batches"]) == 60 and len(t["destinations"]) == 5
    assert len(t["vehicles"]) == 3 + 2  # road fleet + one rail vehicle per hub (S-01d)
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
    """C-10 / A-47: committed practice = generator output; naive FIFO in band per commodity."""
    practice = Path(__file__).parents[2] / "data" / "scenarios" / "practice"
    fresh = generate("practice", 42, 200, 8, 3, 3, tmp_path / "p")
    for f in sorted(practice.glob("*.csv")):
        pd.testing.assert_frame_equal(pd.read_csv(f), pd.read_csv(fresh / f.name))
    out = cli.run(str(practice), "fifo", 42, str(tmp_path / "run"))
    pc = {c["commodity"]: c["spoilage_pct"]
          for c in json.loads((out / "metrics.json").read_text())["per_commodity"]}
    assert abs(pc["tomato"] - 3.25) <= 1.0, pc
    assert abs(pc["banana"] - 2.40) <= 0.8, pc
    assert abs(pc["mango"] - 2.50) <= 0.8, pc
    assert abs(pc["potato"] - 0.86) <= 0.5, pc
    assert 2.3 <= pc["spinach"] <= 3.5, pc
    # onion: horizon-capped, handling-loss-only (A-47) — must stay near its 1 % loss rate
    assert pc["onion"] <= 1.5, pc
    assert max(pc.values()) < 10, pc


def test_practice_uses_rail_and_binding_windows():
    """S-01d: rail arcs are live (≥1 rail vehicle) and some windows bind."""
    practice = Path(__file__).parents[2] / "data" / "scenarios" / "practice"
    sc = load_scenario(practice)
    assert (sc.tables["vehicles"]["mode"] == "rail").any()
    assert (sc.tables["lanes"]["mode"] == "rail").any()
    w = sc.tables["destinations"]
    full = 24 * sc.meta["horizon_days"]
    assert ((w.window_open_h > 0) | (w.window_close_h < full)).any()
    assert ((w.window_open_h == 0) & (w.window_close_h == full)).any()


def test_hidden_suite_loads_and_events_validate():
    """S-01e: every hidden_* scenario loads; event rows parse as Events."""
    from freshroute.events import Event

    root = Path(__file__).parents[2] / "data" / "scenarios"
    hidden = sorted(p for p in root.iterdir() if p.name.startswith("hidden_"))
    assert len(hidden) >= 10, [p.name for p in hidden]
    for scen in hidden:
        sc = load_scenario(scen)  # must not raise
        for row in sc.tables["events"].itertuples():
            Event(event_id=row.event_id, type=row.type, target=row.target,
                  magnitude=float(row.magnitude), at_h=float(row.at_h))
    ev = {p.name for p in hidden if len(load_scenario(p).tables["events"]) > 0}
    assert ev == {"hidden_ev_delay", "hidden_ev_capacity", "hidden_ev_demand",
                  "hidden_ev_price", "hidden_ev_order"}, ev


def test_hidden_seeds_held_out():
    """S-01e: calibration (practice/small, seed 42) never shares a hidden seed."""
    from freshroute.generator import HIDDEN_SEEDS

    assert 42 not in HIDDEN_SEEDS and len(set(HIDDEN_SEEDS)) == len(HIDDEN_SEEDS)


def test_hidden_small_policies_no_crash(tmp_path):
    """S-01e/U-07 dry-run smoke: fifo + fefo run clean on held-out hidden_small."""
    root = Path(__file__).parents[2] / "data" / "scenarios"
    for pol in ("fifo", "fefo"):
        out = cli.run(str(root / "hidden_small"), pol, 101, str(tmp_path / pol))
        assert (out / "metrics.json").exists()


def test_hidden_edge_no_crash(tmp_path):
    """S-01e: expired batch + zero-trip vehicle still produce a validated plan."""
    root = Path(__file__).parents[2] / "data" / "scenarios"
    out = cli.run(str(root / "hidden_edge"), "milp", 206, str(tmp_path / "run"))
    m = json.loads((out / "metrics.json").read_text())
    assert m["kpis"]["violations"] == 0
