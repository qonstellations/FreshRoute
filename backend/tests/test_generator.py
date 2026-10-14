"""Generator output loads, is deterministic, keyed consistently and realistic (A-47..A-50)."""
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
    assert len(t["vehicles"]) == 3 + 2  # road fleet + one rail vehicle per hub
    assert len(t["prices"]) == 6 * 5 * 3 and 0 < len(t["demand"]) <= len(t["prices"])
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


def test_committed_scenarios_match_generator(tmp_path):
    """Every committed scenario is exactly what the generator writes for its seed."""
    from freshroute.generator import COMMITTED, generate_committed

    root = Path(__file__).parents[2] / "data" / "scenarios"
    for name in COMMITTED:
        fresh = generate_committed(name, tmp_path)
        for f in sorted((root / name).iterdir()):
            assert f.read_bytes() == (fresh / f.name).read_bytes(), (name, f.name)


def _practice():
    return load_scenario(Path(__file__).parents[2] / "data" / "scenarios" / "practice")


def test_travel_time_follows_distance():
    from freshroute.generator import _km

    t = _practice().tables
    pos = t["geo"].set_index("node_id")[["lat", "lon"]]
    road = t["lanes"][t["lanes"]["mode"] != "rail"]
    pairs = zip(road.origin, road.dest_id, strict=True)
    km = [_km(tuple(pos.loc[o]), tuple(pos.loc[d])) for o, d in pairs]
    assert pd.Series(km).corr(road.travel_h_p50.reset_index(drop=True)) > 0.95
    assert (road.travel_h_p90 >= road.travel_h_p50).all()


def test_demand_matches_supply_and_is_reachable():
    t = _practice().tables
    ratio = (t["demand"].groupby("commodity").demand_kg_p50.sum()
             / t["batches"].groupby("commodity").qty_kg.sum())
    assert ratio.between(0.85, 1.15).all(), ratio
    # no outlet takes more than half of total demand
    by_dest = t["demand"].groupby("dest_id").demand_kg_p50.sum()
    assert by_dest.max() < 0.5 * by_dest.sum()
    # every demand row sits on a day some vehicle's lane reaches the outlet inside its window
    from freshroute.feasibility import build_arcs
    arcs = build_arcs(_practice())
    ok = {(r.dest_id, r.arrival_day) for r in arcs[arcs.feasible].itertuples()}
    pairs = set(zip(t["demand"].dest_id, t["demand"].day, strict=True))
    assert pairs <= ok, sorted(pairs - ok)


def test_fleet_is_physically_possible():
    t = _practice().tables
    lanes = t["lanes"].set_index(["origin", "mode"]).travel_h_p50.groupby(level=[0, 1]).median()
    for v in t["vehicles"][t["vehicles"]["mode"] != "rail"].itertuples():
        assert v.max_trips_day * 2 * lanes[(v.origin, v.mode)] <= 24, v
    assert set(t["vehicles"].origin) == set(t["lanes"].origin)


def test_expiry_binds_for_perishables():
    """Shelf life is tight enough that naive FIFO loses stock to expiry, not only handling."""
    import json
    from tempfile import TemporaryDirectory

    with TemporaryDirectory() as d:
        out = cli.run(str(Path(__file__).parents[2] / "data" / "scenarios" / "practice"),
                      "fifo", 42, d)
        m = json.loads((out / "metrics.json").read_text())
    b = m["spoilage_breakdown_kg"]
    assert b["origin_expired"] + b["delivered_unsold_expired"] > 0.1 * b["handling_loss"], b
    pc = {c["commodity"]: c["spoilage_pct"] for c in m["per_commodity"]}
    assert pc["spinach"] > 3 * pc["potato"], pc  # leafy perishes, tubers do not
    assert max(pc.values()) < 40, pc


def test_economics_are_plausible():
    """Net margin on revenue sits in a believable range once procurement is charged."""
    import json
    from tempfile import TemporaryDirectory

    with TemporaryDirectory() as d:
        out = cli.run(str(Path(__file__).parents[2] / "data" / "scenarios" / "practice"),
                      "fefo", 42, d)
        e = json.loads((out / "metrics.json").read_text())["economics_inr"]
    assert 0.05 < e["net"] / e["revenue"] < 0.45, e


def test_practice_uses_rail_and_binding_windows():
    """Rail arcs are live (>=1 rail vehicle) and some delivery windows bind."""
    sc = _practice()
    assert (sc.tables["vehicles"]["mode"] == "rail").any()
    assert (sc.tables["lanes"]["mode"] == "rail").any()
    w = sc.tables["destinations"]
    assert ((w.window_open_h > 0) | (w.window_close_h < 24)).any()
    assert sc.meta["window_mode"] == "daily"


def test_hidden_suite_loads_and_events_validate():
    """Every hidden_* scenario loads; event rows parse as Events."""
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
    """Calibration (practice/small, seed 42) never shares a hidden seed."""
    from freshroute.generator import HIDDEN_SEEDS

    assert 42 not in HIDDEN_SEEDS and len(set(HIDDEN_SEEDS)) == len(HIDDEN_SEEDS)


def test_hidden_small_policies_no_crash(tmp_path):
    """Dry-run smoke: fifo + fefo run clean on held-out hidden_small."""
    root = Path(__file__).parents[2] / "data" / "scenarios"
    for pol in ("fifo", "fefo"):
        out = cli.run(str(root / "hidden_small"), pol, 101, str(tmp_path / pol))
        assert (out / "metrics.json").exists()


def test_hidden_edge_no_crash(tmp_path):
    """Expired batch + zero-trip vehicle still produce a validated plan."""
    root = Path(__file__).parents[2] / "data" / "scenarios"
    out = cli.run(str(root / "hidden_edge"), "milp", 206, str(tmp_path / "run"))
    m = json.loads((out / "metrics.json").read_text())
    assert m["kpis"]["violations"] == 0
