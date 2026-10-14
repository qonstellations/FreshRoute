"""`/api` endpoints (ARCHITECTURE.md section 16, DATABASE.md section 11.2).

Every response is a file under outputs/ or data/scenarios/ served verbatim; nothing is computed.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import ValidationError

from freshroute import cli, config, narrator, replan, stress
from freshroute.api import data_access as da
from freshroute.api import jobs
from freshroute.api.schemas import ReplanRequest, RunRequest, StressRequest
from freshroute.config import API_VERSION, SCHEMA_VERSION
from freshroute.events import Event
from freshroute.io import load_scenario

router = APIRouter(prefix="/api")
SCENARIOS = da.ROOT / "data" / "scenarios"
TABLES = ("plan", "trips", "discounts", "sim_ledger", "sim_lots")


def _segment(name: str) -> str:
    """Reject anything that is not a single path segment (no traversal out of outputs/)."""
    if name in ("", ".", "..") or any(c in name for c in "/\\:"):
        raise HTTPException(404, f"not found: {name!r}")
    return name


def _run_dir(run_id: str) -> Path:
    d = da.OUTPUTS / _segment(run_id)
    if not (d / "metrics.json").is_file():
        raise HTTPException(404, f"run {run_id!r} not found")
    return d


def _records(path: Path) -> dict:
    df = pd.read_csv(path).replace([float("inf"), float("-inf")], float("nan"))  # JSON-safe
    return {"columns": list(df.columns),
            "records": df.astype(object).where(df.notna(), None).to_dict(orient="records")}


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "schema_version": SCHEMA_VERSION, "api_version": API_VERSION}


@router.get("/config")
def config_constants() -> dict:
    """config.py public UPPERCASE constants, verbatim (costmodel.py has none: its coefficients
    come from scenario tables)."""
    out = {}
    for k in sorted(vars(config)):
        if k.isupper() and not k.startswith("_"):
            try:
                json.dumps(v := getattr(config, k))
            except TypeError:
                continue
            out[k] = v
    return out


@router.get("/scenarios")
def scenarios() -> list[dict]:
    out = []
    for p in sorted(SCENARIOS.glob("*/scenario.json")):
        m = json.loads(p.read_text(encoding="utf-8"))
        out.append({k: m.get(k) for k in ("name", "source", "horizon_days", "window_mode")})
    return sorted(out, key=lambda s: str(s["name"]))


@router.get("/scenarios/{name}/geo")
def geo(name: str) -> list[dict]:
    p = SCENARIOS / _segment(name) / "geo.csv"
    if not p.is_file():
        raise HTTPException(404, f"no geo.csv for scenario {name!r}")
    return _records(p)["records"]


@router.get("/runs")
def runs() -> dict:
    ids = da.list_runs(da.OUTPUTS)
    ms = [(r, da.load_metrics(r, da.OUTPUTS)[0]) for r in ids]
    # run_id = directory name: the key every /runs/{run_id} endpoint resolves (a CLI --out
    # directory may differ from metrics.run_id)
    return {"runs": [{"run_id": r, "scenario": m.get("scenario"),
                      "policy": m.get("policy"), "seed": m.get("seed"),
                      "has_ladder": da.load_ladder(m.get("scenario"), m.get("seed"),
                                                   da.OUTPUTS) is not None} for r, m in ms],
            "fixture": not ids}


@router.get("/runs/{run_id}")
def run(run_id: str) -> dict:
    if not da.list_runs(da.OUTPUTS):
        fixture, _ = da.load_metrics(None, da.OUTPUTS)
        if run_id == fixture.get("run_id"):
            return {**fixture, "baseline": None, "validation": None, "manifest": None,
                    "fixture": True}
    _run_dir(run_id)
    m, _ = da.load_metrics(run_id, da.OUTPUTS)
    return {**m, "baseline": da.load_baseline(m.get("scenario"), m.get("seed"), da.OUTPUTS),
            "validation": da.load_validation(run_id, da.OUTPUTS),
            "manifest": da.load_manifest(run_id, da.OUTPUTS), "fixture": False}


@router.get("/runs/{run_id}/tables/{table}")
def table(run_id: str, table: str, format: str = "json"):
    p = _run_dir(run_id) / f"{table}.csv"
    if table not in TABLES or not p.is_file():
        raise HTTPException(404, f"no table {table!r} in run {run_id!r}")
    if format == "csv":
        return FileResponse(p, media_type="text/csv", filename=p.name)
    return _records(p)


@router.get("/runs/{run_id}/reason-cards")
def reason_cards(run_id: str):
    return da._read_json(_run_dir(run_id) / "reason_cards.json")


@router.get("/runs/{run_id}/dispatch-sheet")
def dispatch_sheet(run_id: str):
    d = _run_dir(run_id)
    csv, txt = d / "dispatch_sheet.csv", d / "dispatch_sheet.txt"
    if not (csv.is_file() and txt.is_file()):
        return None
    return {"csv": _records(csv)["records"], "text": txt.read_text(encoding="utf-8")}


@router.get("/ladder")
def ladder(scenario: str, seed: int) -> dict:
    d = da.OUTPUTS / _segment(f"{scenario}__ladder__s{seed}")
    lad = da._read_json(d / "ladder.json")
    if lad is None:
        raise HTTPException(404, f"no ladder for {scenario!r} seed {seed}")
    return {"ladder": lad, "waterfall": da._read_json(d / "waterfall.json")}


@router.post("/runs", status_code=202)
def start_run(req: RunRequest) -> dict:
    if req.policy in cli.BLOCKED_POLICIES:
        raise HTTPException(400, cli.ORGANIZER_BASELINE_BLOCKED)
    if req.policy not in cli.POLICIES:
        raise HTTPException(400, f"unknown policy {req.policy!r}; available: "
                                 f"{', '.join(cli.POLICIES)}")
    nv = bool(req.flags.get("newsvendor"))
    if nv and req.policy not in cli.NEWSVENDOR_POLICIES:
        raise HTTPException(400, f"--newsvendor needs a MILP policy, not {req.policy!r}")
    scen = _scenario_path(req.scenario)
    try:
        name = load_scenario(scen).name
    except (OSError, ValueError, KeyError) as e:
        raise HTTPException(400, f"scenario {req.scenario!r} failed to load: {e}") from e
    run_id = f"{name}__{req.policy}__s{req.seed}{'__nv' if nv else ''}"  # id cli.run computes
    job = jobs.live_job(da.OUTPUTS, run_id)
    if job is None:
        job = jobs.submit(da.OUTPUTS, run_id, scen, req.policy, req.seed, nv)
    return {"run_id": run_id, "status": job["state"]}


@router.get("/runs/{run_id}/status")
def status(run_id: str) -> dict:
    job = jobs.read_job(da.OUTPUTS, _segment(run_id))
    if job is None:
        if not (da.OUTPUTS / run_id / "metrics.json").is_file():
            raise HTTPException(404, f"no job or run {run_id!r}")
        job = {"state": "done", "started_utc": None, "finished_utc": None, "error": None}
    elif job["state"] == "running" and jobs.live_job(da.OUTPUTS, run_id) is None:
        job = {**job, "state": "error", "error": "stale job: the server restarted; submit again"}
    return {k: job.get(k) for k in ("state", "started_utc", "finished_utc", "error")}


def _scenario_path(scenario: str) -> str:
    """A bare scenario name (as served in metrics.json) resolves under data/scenarios/; a
    relative path resolves against the repo root, never the server's working directory."""
    bare = not any(c in scenario for c in ("/", chr(92), ":"))
    if bare and (SCENARIOS / scenario).is_dir():
        return str(SCENARIOS / scenario)
    p = Path(scenario)
    return str(p if p.is_absolute() else da.ROOT / p)


def _out_dir(scenario: str, kind: str, seed: int) -> Path:
    return da.OUTPUTS / _segment(f"{scenario}__{kind}__s{seed}")


@router.get("/stress")
def stress_summary(scenario: str, seed: int) -> dict:
    d = _out_dir(scenario, "stress", seed)
    summary = da._read_json(d / "stress_summary.json")
    if summary is None:
        raise HTTPException(404, f"no stress run for {scenario!r} seed {seed}")
    rows = _records(d / "stress.csv")["records"] if (d / "stress.csv").is_file() else None
    return {"summary": summary, "rows": rows}


@router.post("/stress", status_code=202)
def start_stress(req: StressRequest) -> dict:
    if req.policy not in cli.POLICIES:
        raise HTTPException(400, f"policy {req.policy!r} cannot be stressed")
    try:
        name = load_scenario(_scenario_path(req.scenario)).name
    except (OSError, ValueError, KeyError) as e:
        raise HTTPException(400, f"scenario {req.scenario!r} failed to load: {e}") from e
    job_id = f"{name}__stress__s{req.seed}"
    job = jobs.live_job(da.OUTPUTS, job_id)
    if job is None:
        d = da.OUTPUTS / job_id
        job = jobs.submit_call(da.OUTPUTS, job_id, lambda: stress.run_stress(
            _scenario_path(req.scenario), req.policy, req.n, req.seed, str(d)),
            d / "stress_summary.json", scenario=req.scenario, policy=req.policy, seed=req.seed)
    return {"run_id": job_id, "status": job["state"]}


@router.get("/sensitivity")
def sensitivity(scenario: str, seed: int) -> dict:
    p = _out_dir(scenario, "sensitivity", seed) / "sensitivity.csv"
    if not p.is_file():
        raise HTTPException(404, f"no sensitivity run for {scenario!r} seed {seed}")
    return {"records": _records(p)["records"]}


@router.post("/replan", status_code=202)
def start_replan(req: ReplanRequest) -> dict:
    run_dir = _run_dir(req.run_id)
    try:
        ev = Event(**req.event)
    except (ValidationError, TypeError) as e:
        raise HTTPException(400, f"invalid event: {e}") from e
    job_id = f"{req.run_id}__replan__{_segment(ev.event_id)}"
    job = jobs.live_job(da.OUTPUTS, job_id)
    if job is None:
        job = jobs.submit_call(da.OUTPUTS, job_id, lambda: replan.replan_run(run_dir, ev),
                               run_dir / "replan" / ev.event_id / "diff.json",
                               event_id=ev.event_id)
    return {"run_id": req.run_id, "event_id": ev.event_id, "status": job["state"]}


@router.get("/runs/{run_id}/replan/{event_id}")
def replan_result(run_id: str, event_id: str) -> dict:
    d = _run_dir(run_id) / "replan" / _segment(event_id)
    diff, metrics = da._read_json(d / "diff.json"), da._read_json(d / "metrics.json")
    if diff is None or metrics is None:
        raise HTTPException(404, f"no replan {event_id!r} for run {run_id!r}")
    return {"diff": diff, "narration": narrator.template_narration(diff, metrics)}
