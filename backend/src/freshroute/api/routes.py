"""`/api` endpoints (ARCHITECTURE.md section 16, DATABASE.md section 11.2).

Every response is a file under outputs/ or data/scenarios/ served verbatim; nothing is computed.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from freshroute import cli
from freshroute.api import data_access as da
from freshroute.api import jobs
from freshroute.api.schemas import RunRequest
from freshroute.config import API_VERSION, SCHEMA_VERSION
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
    df = pd.read_csv(path)
    return {"columns": list(df.columns),
            "records": df.astype(object).where(df.notna(), None).to_dict(orient="records")}


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "schema_version": SCHEMA_VERSION, "api_version": API_VERSION}


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
    ms = [da.load_metrics(r, da.OUTPUTS)[0] for r in ids]
    return {"runs": [{"run_id": m.get("run_id"), "scenario": m.get("scenario"),
                      "policy": m.get("policy"), "seed": m.get("seed"),
                      "has_ladder": da.load_ladder(m.get("scenario"), m.get("seed"),
                                                   da.OUTPUTS) is not None} for m in ms],
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
    if req.flags.get("newsvendor"):
        raise HTTPException(400, "flag 'newsvendor' is not implemented by the CLI yet")
    try:
        name = load_scenario(req.scenario).name
    except (OSError, ValueError, KeyError) as e:
        raise HTTPException(400, f"scenario {req.scenario!r} failed to load: {e}") from e
    run_id = f"{name}__{req.policy}__s{req.seed}"  # same id cli.run computes
    job = jobs.read_job(da.OUTPUTS, run_id)
    if not (job and job["state"] == "running"):
        job = jobs.submit(da.OUTPUTS, run_id, req.scenario, req.policy, req.seed)
    return {"run_id": run_id, "status": job["state"]}


@router.get("/runs/{run_id}/status")
def status(run_id: str) -> dict:
    job = jobs.read_job(da.OUTPUTS, _segment(run_id))
    if job is None:
        if not (da.OUTPUTS / run_id / "metrics.json").is_file():
            raise HTTPException(404, f"no job or run {run_id!r}")
        job = {"state": "done", "started_utc": None, "finished_utc": None, "error": None}
    return {k: job.get(k) for k in ("state", "started_utc", "finished_utc", "error")}
