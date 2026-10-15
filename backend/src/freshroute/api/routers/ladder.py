"""Ladder, stress, sensitivity and frontier outputs (DATABASE.md section 11.2)."""
from __future__ import annotations

from fastapi import APIRouter

from freshroute.api import data_access as da
from freshroute.api import deps, jobs
from freshroute.api.schemas import StressRequest, SubmitResponse
from freshroute.api.services import outputs as out
from freshroute.api.services import runs as svc
from freshroute.runs import runner, stress

router = APIRouter(prefix="/api")


@router.get("/ladder")
def ladder(scenario: str, seed: int) -> dict:
    d = out.out_dir(scenario, "ladder", seed)
    lad = da.read_json(d / "ladder.json")
    if lad is None:
        raise deps.NotFound(f"no ladder for {scenario!r} seed {seed}")
    return {"ladder": lad, "waterfall": da.read_json(d / "waterfall.json")}


@router.get("/stress")
def stress_summary(scenario: str, seed: int) -> dict:
    d = out.out_dir(scenario, "stress", seed)
    summary = da.read_json(d / "stress_summary.json")
    if summary is None:
        raise deps.NotFound(f"no stress run for {scenario!r} seed {seed}")
    rows = out.records(d / "stress.csv")["records"] if (d / "stress.csv").is_file() else None
    return {"summary": summary, "rows": rows}


@router.post("/stress", status_code=202)
def start_stress(req: StressRequest) -> SubmitResponse:
    if req.policy not in runner.POLICIES:
        raise deps.BadRequest(f"policy {req.policy!r} cannot be stressed")
    scen, name = svc.loaded_scenario(req.scenario)
    job_id = out.name(name, "stress", req.seed)
    d = deps.outputs() / job_id
    job = jobs.queue.submit_if_idle(
        deps.outputs(), job_id,
        lambda: stress.run_stress(scen, req.policy, req.n, req.seed, str(d)),
        d / "stress_summary.json", scenario=req.scenario, policy=req.policy, seed=req.seed)
    return SubmitResponse(run_id=job_id, status=job["state"])


@router.get("/sensitivity")
def sensitivity(scenario: str, seed: int) -> dict:
    p = out.out_dir(scenario, "sensitivity", seed) / "sensitivity.csv"
    if not p.is_file():
        raise deps.NotFound(f"no sensitivity run for {scenario!r} seed {seed}")
    return {"records": out.records(p)["records"]}


@router.get("/frontier")
def frontier(scenario: str, seed: int) -> dict:
    p = out.out_dir(scenario, "frontier", seed) / "frontier.csv"
    if not p.is_file():
        raise deps.NotFound(f"no frontier run for {scenario!r} seed {seed}")
    return {"records": out.records(p)["records"]}
