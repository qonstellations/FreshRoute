"""Replan job and result (DATABASE.md section 11.2)."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import ValidationError

from freshroute import narrator
from freshroute.api import data_access as da
from freshroute.api import deps, jobs
from freshroute.api.schemas import ReplanRequest, ReplanSubmitResponse
from freshroute.api.services import outputs as out
from freshroute.events import Event
from freshroute.runs import replan

router = APIRouter(prefix="/api")


@router.post("/replan", status_code=202)
def start_replan(req: ReplanRequest) -> ReplanSubmitResponse:
    run_dir = out.run_dir(req.run_id)
    try:
        ev = Event(**req.event)
    except (ValidationError, TypeError) as e:
        raise deps.BadRequest(f"invalid event: {e}") from e
    job_id = f"{req.run_id}__replan__{deps.segment(ev.event_id)}"
    job = jobs.queue.submit_if_idle(
        deps.outputs(), job_id, lambda: replan.replan_run(run_dir, ev),
        run_dir / "replan" / ev.event_id / "diff.json", event_id=ev.event_id)
    return ReplanSubmitResponse(run_id=req.run_id, event_id=ev.event_id, status=job["state"])


@router.get("/runs/{run_id}/replan/{event_id}")
def replan_result(run_id: str, event_id: str) -> dict:
    d = out.run_dir(run_id) / "replan" / deps.segment(event_id)
    diff, metrics = da.read_json(d / "diff.json"), da.read_json(d / "metrics.json")
    if diff is None or metrics is None:
        raise deps.NotFound(f"no replan {event_id!r} for run {run_id!r}")
    return {"diff": diff, "narration": narrator.template_narration(diff, metrics)}
