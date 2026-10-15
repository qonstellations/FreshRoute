"""HTTP API models (ARCHITECTURE.md section 16, DATABASE.md section 11.2).

Run/table payloads are files served verbatim, so only requests and small envelopes have models.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from freshroute.config import DEFAULT_SEED, MC_N


class RunRequest(BaseModel):
    scenario: str
    policy: str
    seed: int = DEFAULT_SEED
    flags: dict[str, bool] = {}


class StressRequest(BaseModel):
    scenario: str
    policy: str = "milp"
    seed: int = DEFAULT_SEED
    n: int = Field(MC_N, ge=1, le=2000)


class ReplanRequest(BaseModel):
    run_id: str
    event: dict


class HealthResponse(BaseModel):
    status: str
    schema_version: int
    api_version: int


class SubmitResponse(BaseModel):
    run_id: str
    status: str


class ReplanSubmitResponse(SubmitResponse):
    event_id: str


class Progress(BaseModel):
    version: int  # published plans so far; the run directory holds the latest
    net_inr: float
    final: bool
    elapsed_s: float


class StatusResponse(BaseModel):
    state: str
    progress: Progress | None = None
    started_utc: str | None
    finished_utc: str | None
    error: str | None
