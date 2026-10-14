"""Event-driven replan (ARCHITECTURE.md section 14.2; outputs DATABASE.md section 5.13).

apply event -> freeze shipments with dispatch_h <= at_h -> residual scenario (undispatched
stock; dispatch >= at_h; frozen trips, arrivals and deliveries subtracted from C3/C4/C5) ->
MILP re-solve -> one simulator scores both the old plan in the changed world and the
replanned plan. The solver objective is never reported.
"""
from __future__ import annotations

import json
import math
import time
from dataclasses import replace
from pathlib import Path

import pandas as pd

from freshroute.config import FLOAT_TOL, OVERSHIP_SLACK, REPLAN_TIME_LIMIT_S
from freshroute.data.events import Event, apply_event, lane_mask, load_event
from freshroute.data.io import Scenario, load_scenario
from freshroute.domain.discount import COLUMNS as DISCOUNT_COLUMNS
from freshroute.domain.discount import build_discounts
from freshroute.domain.shelflife import usable_life_at_arrival
from freshroute.engine import metrics as M
from freshroute.engine.simulator import simulate
from freshroute.policies.base import PLAN_COLUMNS, TRIP_COLUMNS
from freshroute.policies.milp import MilpPolicy
from validator.validate import ValidationReport, validate

KPI_KEYS = ("spoilage_kg", "spoilage_pct", "demand_fulfillment_pct", "min_dest_fill_pct",
            "net_inr", "violations")
# plan.csv columns a frozen shipment keeps verbatim; a route_delay may re-time the others
DECISION_COLUMNS = ("shipment_id", "batch_id", "dest_id", "vehicle_id", "trip_id", "mode",
                    "dispatch_day", "dispatch_h", "kg", "margin_inr_kg", "priority_rank",
                    "priority_score", "policy")


def retime(world: Scenario, plan: pd.DataFrame, ev: Event) -> pd.DataFrame:
    """route_delay: shipments on matching lanes still travelling at at_h get the changed
    world's arrival and usable life (DATABASE.md section 6). Other events: unchanged."""
    if ev.type != "route_delay" or plan.empty:
        return plan
    t = world.tables
    b = t["batches"].set_index("batch_id")
    com = t["commodities"].set_index("commodity")
    dst = t["destinations"].set_index("dest_id")
    lanes = t["lanes"].set_index(["origin", "dest_id", "mode"])
    p = plan.copy()
    keys = pd.DataFrame({"origin": p.batch_id.map(b.origin_hub), "dest_id": p.dest_id,
                         "mode": p["mode"]})
    hit = lane_mask(keys, ev.target) & (p.arrival_h > ev.at_h + FLOAT_TOL)
    for col in ("arrival_h", "usable_life_at_arrival_h", "slack_h"):
        p[col] = p[col].astype(float)
    for i in p.index[hit]:
        r = p.loc[i]
        bt, ln = b.loc[r.batch_id], lanes.loc[(b.origin_hub[r.batch_id], r.dest_id, r["mode"])]
        c = com.loc[bt.commodity]
        arr = float(r.dispatch_h) + float(ln.travel_h_p50)
        u = usable_life_at_arrival(
            bt.remaining_shelf_life_h, r.dispatch_h - bt.available_from_h, ln.travel_h_p50,
            dst.handling_time_h[r.dest_id], bt.storage_temp_c, ln.transit_temp_c, c.ref_temp_c,
            c.q10)
        p.loc[i, ["arrival_h", "usable_life_at_arrival_h", "slack_h"]] = [
            arr, u, u - c.min_sell_window_h]
        p.loc[i, "arrival_day"] = math.floor(arr / 24 + FLOAT_TOL)
    return p


def residual(world: Scenario, frozen: pd.DataFrame, at_h: float) -> tuple[Scenario, dict]:
    """Residual scenario + MILP ctx: stock minus frozen kg, vehicles available from at_h,
    frozen trips / arrivals / deliveries subtracted from C3 / C4 / C5 (section 14.2)."""
    t = world.tables
    com = t["batches"].set_index("batch_id").commodity
    b = t["batches"].copy()
    b["qty_kg"] = b.qty_kg - b.batch_id.map(frozen.groupby("batch_id").kg.sum()).fillna(0.0)
    v = t["vehicles"].copy()
    v["available_from_h"] = v.available_from_h.clip(lower=at_h)
    f = frozen.assign(commodity=frozen.batch_id.map(com),
                      arrival_day=frozen.arrival_day.astype(int),
                      dispatch_day=frozen.dispatch_day.astype(int))
    got = f.groupby(["dest_id", "commodity", "arrival_day"]).kg.sum().to_dict()
    dem = t["demand"].set_index(["dest_id", "commodity", "day"]).demand_kg_p50
    # C5 cap is target * (1 + slack): residual target keeps frozen + new <= p50 * (1 + slack)
    override = {k: max(0.0, float(p50) - got.get(k, 0.0) / (1 + OVERSHIP_SLACK))
                for k, p50 in dem.items()}
    used = {"trips": {k: int(n) for k, n in f.groupby(["vehicle_id", "dispatch_day"])
                      .trip_id.nunique().items()},
            "recv": f.groupby(["dest_id", "arrival_day"]).kg.sum().to_dict(),
            "fill": f.groupby("dest_id").kg.sum().to_dict()}
    sc = replace(world, tables={**t, "batches": b[b.qty_kg > FLOAT_TOL].reset_index(drop=True),
                                "vehicles": v})
    return sc, {"demand_cap_override": override, "residual_use": used}


def _renumber(new: pd.DataFrame, trips: pd.DataFrame, old: pd.DataFrame, frozen: pd.DataFrame):
    """New shipment ids after the old plan's, ranks after the frozen ones, trip ids that do
    not collide with a frozen trip on the same (vehicle, dest, day)."""
    top = {}
    for tid in frozen.trip_id:
        pre, k = tid.rsplit("-", 1)
        top[pre] = max(top.get(pre, 0), int(k))

    def tid(x: str) -> str:
        pre, k = x.rsplit("-", 1)
        return f"{pre}-{int(k) + top.get(pre, 0)}"

    start = max((int(s[1:]) for s in old.shipment_id), default=0)
    new = new.assign(trip_id=new.trip_id.map(tid),
                     shipment_id=[f"S{start + i + 1:04d}" for i in range(len(new))],
                     priority_rank=new.priority_rank + int(frozen.priority_rank.max()
                                                           if len(frozen) else 0))
    return new, trips.assign(trip_id=trips.trip_id.map(tid))


def _frozen_trips(old_trips: pd.DataFrame, frozen: pd.DataFrame) -> pd.DataFrame:
    """Old trip rows of frozen trips; kg re-summed when a trip was only partly frozen."""
    tr = old_trips[old_trips.trip_id.isin(set(frozen.trip_id))].copy()
    kg = tr.trip_id.map(frozen.groupby("trip_id").kg.sum())
    part = (tr.kg_total - kg).abs() > FLOAT_TOL
    if part.any():
        tr.loc[part, "cost_var_inr"] = tr.cost_var_inr[part] * kg[part] / tr.kg_total[part]
        tr.loc[part, "kg_total"] = kg[part]
        tr.loc[part, "utilization_pct"] = 100 * kg[part] / tr.capacity_kg[part]
    return tr


def _validate(world: Scenario, plan, disc, frozen) -> ValidationReport:
    """Independent validator on the whole plan in the changed world. A violation the frozen
    shipments already cause on their own (in-transit delay, capacity drop on a trip that has
    left) cannot be replanned away: it is reported as a FROZEN_<code> warning (A-43)."""
    rep = validate(world, plan, disc, overship_slack=OVERSHIP_SLACK)
    base = validate(world, frozen).violations if len(frozen) else []
    inherited = {(x["code"], x["shipment_id"], x["detail"]) for x in base}
    keep, warn = [], list(rep.warnings)
    for x in rep.violations:
        if (x["code"], x["shipment_id"], x["detail"]) in inherited:
            warn.append({**x, "code": "FROZEN_" + x["code"]})
        else:
            keep.append(x)
    return ValidationReport(keep, warn)


def _score(world, plan, disc, frozen, run_id, policy, seed):
    report = _validate(world, plan, disc, frozen)
    sim = simulate(world, plan, disc)
    sim.update(run_id=run_id, policy=policy, seed=seed, violations=report.violation_total)
    return M.compute(world, plan, disc, sim), report


def _alloc(plan: pd.DataFrame) -> dict:
    """batch -> (dest, dispatch_day, kg) with the most kg, ties by key."""
    out = {}
    g = plan.groupby(["batch_id", "dest_id", "dispatch_day"]).kg.sum()
    for (bid, d, day), kg in sorted(g.items()):
        if bid not in out or kg > out[bid][2] + FLOAT_TOL:
            out[bid] = (d, int(day), float(kg))
    return out


def _moved(old_live: pd.DataFrame, new_live: pd.DataFrame) -> list[dict]:
    """Batches whose main undispatched allocation changed; dest_id None = unshipped."""
    a, b = _alloc(old_live), _alloc(new_live)
    out = []
    for bid in sorted(set(a) | set(b)):
        f, t = a.get(bid, (None, None, 0.0)), b.get(bid, (None, None, 0.0))
        if f[:2] != t[:2]:
            out.append({"batch_id": bid, "from": {"dest_id": f[0], "dispatch_day": f[1]},
                        "to": {"dest_id": t[0], "dispatch_day": t[1]},
                        "kg": t[2] if t[0] is not None else f[2]})
    return out


def _discount_changes(old: pd.DataFrame, new: pd.DataFrame) -> list[dict]:
    o = old.set_index(["lot_id", "day"]).discount_pct if len(old) else pd.Series(dtype=float)
    n = new.set_index(["lot_id", "day"]).discount_pct if len(new) else pd.Series(dtype=float)
    out = []
    for lot, day in sorted(set(o.index) | set(n.index)):
        f, t = float(o.get((lot, day), 0.0)), float(n.get((lot, day), 0.0))
        if abs(f - t) > FLOAT_TOL:
            out.append({"lot_id": lot, "day": int(day), "from_pct": f, "to_pct": t})
    return out


def _cat(a: pd.DataFrame, b: pd.DataFrame, cols) -> pd.DataFrame:
    parts = [x for x in (a, b) if len(x)] or [a]  # empty frames would muddle dtypes
    return pd.concat(parts, ignore_index=True).reindex(columns=list(cols))


def replan(world0: Scenario, old_plan: pd.DataFrame, old_trips: pd.DataFrame,
           old_disc: pd.DataFrame, ev: Event, *, markdown: bool, run_id: str,
           seed: int) -> dict:
    """Return {"world", "plan", "trips", "discounts", "metrics", "validation", "diff"}."""
    t0 = time.perf_counter()
    world = apply_event(world0, ev)
    old = retime(world, old_plan, ev)
    is_frozen = old.is_frozen.astype(bool) | (old.dispatch_h <= ev.at_h + FLOAT_TOL)
    frozen = old[is_frozen].assign(is_frozen=True)
    sc, ctx = residual(world, frozen, ev.at_h)
    policy = "milp_markdown" if markdown else "milp"
    if sc.tables["batches"].empty:
        new = pd.DataFrame(columns=list(PLAN_COLUMNS))
        new_trips, solver = pd.DataFrame(columns=list(TRIP_COLUMNS)), None
    else:
        res = MilpPolicy().plan(sc, {"seed": seed, "time_limit_s": REPLAN_TIME_LIMIT_S,
                                     "warm_start": old[~is_frozen], **ctx})
        new, new_trips, solver = res.plan.assign(policy=policy), res.trips, res.solver
        new, new_trips = _renumber(new, new_trips, old_plan, frozen)
    plan = _cat(frozen, new, PLAN_COLUMNS)
    trips = _cat(_frozen_trips(old_trips, frozen), new_trips, TRIP_COLUMNS)
    disc = (build_discounts(world, plan) if markdown
            else pd.DataFrame(columns=list(DISCOUNT_COLUMNS)))
    solve_s = time.perf_counter() - t0

    rid = f"{run_id}__{ev.event_id}"
    m_old, _ = _score(world, old, old_disc, frozen, rid, policy, seed)
    m_new, report = _score(world, plan, disc, frozen, rid, policy, seed)
    k_old = {k: m_old["kpis"][k] for k in KPI_KEYS}
    k_new = {k: m_new["kpis"][k] for k in KPI_KEYS}
    diff = {
        "event_id": ev.event_id, "at_h": ev.at_h, "frozen_shipments": len(frozen),
        "moved_batches": _moved(old[~is_frozen], new),
        "discount_changes": _discount_changes(old_disc, disc),
        "kpis_old_plan_under_event": k_old, "kpis_replanned": k_new,
        "delta_kpis": {k: k_new[k] - k_old[k] for k in KPI_KEYS},
        "solver": None if solver is None else {
            k: solver.get(k) for k in ("status", "mip_gap", "fallback_used")},
        "solve_seconds": solve_s,
    }
    return {"world": world, "plan": plan, "trips": trips, "discounts": disc,
            "metrics": m_new, "validation": report, "diff": diff}


def _load_world(run_dir: Path) -> tuple[Scenario, dict]:
    """Scenario as the run saw it: a replan dir (has event.json) is its parent run's world
    with its event applied, so events chain (<run>/replan/<e1>/replan/<e2>/)."""
    if (run_dir / "event.json").exists():
        world, man = _load_world(run_dir.parent.parent)
        return apply_event(world, load_event(run_dir / "event.json")), man
    man = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
    return load_scenario(man["scenario"]), man


def _read_csv(path: Path, cols) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame(columns=list(cols))


def replan_run(run_dir: str | Path, event: str | Path | Event, out: str | Path | None = None
               ) -> Path:
    """`freshroute replan`: replan a run (or a replan dir) for one event; write
    <run_dir>/replan/<event_id>/ (DATABASE.md 5.13) and return it."""
    run_dir = Path(run_dir)
    ev = event if isinstance(event, Event) else load_event(event)
    world0, man = _load_world(run_dir)
    m = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    r = replan(world0, pd.read_csv(run_dir / "plan.csv"), pd.read_csv(run_dir / "trips.csv"),
               _read_csv(run_dir / "discounts.csv", DISCOUNT_COLUMNS), ev,
               markdown=bool(man["flags"]["markdown"]), run_id=m["run_id"], seed=m["seed"])
    out_dir = Path(out) if out else run_dir / "replan" / ev.event_id
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "event.json").write_text(ev.model_dump_json(indent=2) + "\n", encoding="utf-8")
    r["plan"].to_csv(out_dir / "plan.csv", index=False)
    r["trips"].to_csv(out_dir / "trips.csv", index=False)
    r["discounts"].to_csv(out_dir / "discounts.csv", index=False)
    (out_dir / "metrics.json").write_text(json.dumps(r["metrics"], indent=2) + "\n",
                                          encoding="utf-8")
    r["validation"].write(out_dir / "validation.json")
    (out_dir / "diff.json").write_text(json.dumps(r["diff"], indent=2) + "\n", encoding="utf-8")
    return out_dir
