"""Run list/detail, tables, reason cards, dispatch sheet, run start and status
(DATABASE.md section 11.2)."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import FileResponse

from freshroute.api import data_access as da
from freshroute.api import deps
from freshroute.api.schemas import RunRequest, StatusResponse, SubmitResponse
from freshroute.api.services import outputs as out
from freshroute.api.services import runs as svc

router = APIRouter(prefix="/api")
TABLES = ("plan", "trips", "discounts", "sim_ledger", "sim_lots")


@router.get("/runs")
def runs() -> dict:
    return svc.list_runs()


@router.get("/runs/{run_id}")
def run(run_id: str) -> dict:
    return svc.run_detail(run_id)


@router.get("/runs/{run_id}/tables/{table}")
def table(run_id: str, table: str, format: str = "json"):
    p = out.run_dir(run_id) / f"{table}.csv"
    if table not in TABLES or not p.is_file():
        raise deps.NotFound(f"no table {table!r} in run {run_id!r}")
    if format == "csv":
        return FileResponse(p, media_type="text/csv", filename=p.name)
    return out.records(p)


@router.get("/runs/{run_id}/reason-cards")
def reason_cards(run_id: str):
    # null when absent (test_api relies on it)
    return da.read_json(out.run_dir(run_id) / "reason_cards.json")


@router.get("/runs/{run_id}/dispatch-sheet")
def dispatch_sheet(run_id: str):
    d = out.run_dir(run_id)
    csv, txt = d / "dispatch_sheet.csv", d / "dispatch_sheet.txt"
    if not (csv.is_file() and txt.is_file()):
        return None  # client types this as DispatchSheet | null
    return {"csv": out.records(csv)["records"], "text": txt.read_text(encoding="utf-8")}


@router.post("/runs", status_code=202)
def start_run(req: RunRequest) -> SubmitResponse:
    return SubmitResponse(**svc.start_run(req))


@router.get("/runs/{run_id}/status")
def status(run_id: str) -> StatusResponse:
    return StatusResponse(**svc.job_status(run_id))
