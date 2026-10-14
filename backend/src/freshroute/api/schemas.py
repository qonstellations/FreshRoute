"""Request bodies for the HTTP API (ARCHITECTURE.md section 16, DATABASE.md section 11.2).

Responses are files served verbatim, so they have no models here.
"""
from __future__ import annotations

from pydantic import BaseModel

from freshroute.config import DEFAULT_SEED, MC_N


class RunRequest(BaseModel):
    scenario: str
    policy: str
    seed: int = DEFAULT_SEED
    flags: dict[str, bool] = {}


class StressRequest(BaseModel):
    scenario: str
    policy: str = "milp_markdown"
    seed: int = DEFAULT_SEED
    n: int = MC_N


class ReplanRequest(BaseModel):
    run_id: str
    event: dict
