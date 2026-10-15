"""Run listing/detail assembly, job status, run start (ARCHITECTURE.md section 16,
DATABASE.md section 11.2)."""
from __future__ import annotations

from freshroute.api import data_access as da
from freshroute.api import deps, jobs
from freshroute.api.schemas import RunRequest
from freshroute.api.services import outputs as out
from freshroute.data.io import load_scenario
from freshroute.runs import runner


def list_runs() -> dict:
    o = deps.outputs()
    ids = da.list_runs(o)
    ms = [(r, da.load_metrics(r, o)[0]) for r in ids]
    # run_id = directory name: the key every /runs/{run_id} endpoint resolves (a CLI --out
    # directory may differ from metrics.run_id)
    return {"runs": [{"run_id": r, "scenario": m.get("scenario"), "policy": m.get("policy"),
                      "seed": m.get("seed"),
                      "has_ladder": da.load_ladder(m.get("scenario"), m.get("seed"), o) is not None}
                     for r, m in ms],
            "fixture": not ids}


def run_detail(run_id: str) -> dict:
    o = deps.outputs()
    if not da.list_runs(o):
        fixture, _ = da.load_metrics(None, o)
        if run_id == fixture.get("run_id"):
            return {**fixture, "baseline": None, "validation": None, "manifest": None,
                    "fixture": True}
    out.run_dir(run_id)
    m, _ = da.load_metrics(run_id, o)
    return {**m, "baseline": da.load_baseline(m.get("scenario"), m.get("seed"), o),
            "validation": da.load_validation(run_id, o),
            "manifest": da.load_manifest(run_id, o), "fixture": False}


def job_status(run_id: str) -> dict:
    o = deps.outputs()
    job = jobs.read_job(o, deps.segment(run_id))
    if job is None:
        if not (o / run_id / "metrics.json").is_file():
            raise deps.NotFound(f"no job or run {run_id!r}")
        job = {"state": "done", "started_utc": None, "finished_utc": None, "error": None}
    elif job["state"] == "running" and jobs.queue.live_job(o, run_id) is None:  # stale repair
        job = {**job, "state": "error", "error": "stale job: the server restarted; submit again"}
    return {k: job.get(k) for k in ("state", "started_utc", "finished_utc", "error", "progress")}


def loaded_scenario(scenario: str) -> tuple[str, str]:
    """(resolved scenario path, scenario name); 400 when it does not load."""
    path = deps.scenario_path(scenario)
    try:
        return path, load_scenario(path).name
    except (OSError, ValueError, KeyError) as e:
        raise deps.BadRequest(f"scenario {scenario!r} failed to load: {e}") from e


def start_run(req: RunRequest) -> dict:
    if req.policy in runner.BLOCKED_POLICIES:
        raise deps.BadRequest(runner.ORGANIZER_BASELINE_BLOCKED)
    if req.policy not in runner.POLICIES:
        raise deps.BadRequest(f"unknown policy {req.policy!r}; available: "
                              f"{', '.join(runner.POLICIES)}")
    nv = bool(req.flags.get("newsvendor"))
    if nv and req.policy not in runner.NEWSVENDOR_POLICIES:
        raise deps.BadRequest(f"--newsvendor needs a MILP policy, not {req.policy!r}")
    scen, scen_name = loaded_scenario(req.scenario)
    run_id = out.name(scen_name, req.policy, req.seed, nv)  # id runner.run computes
    run_dir = deps.outputs() / run_id
    job = jobs.queue.submit_if_idle(
        deps.outputs(), run_id,
        lambda: runner.run(
            scen, req.policy, req.seed, str(run_dir), newsvendor=nv,
            on_progress=lambda p: jobs.queue.update(deps.outputs(), run_id, progress=p)),
        run_dir / "metrics.json", scenario=scen, policy=req.policy, seed=req.seed)
    return {"run_id": run_id, "status": job["state"]}
