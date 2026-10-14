"""Health, config constants, scenarios (DATABASE.md section 11.2)."""
from __future__ import annotations

import json

from fastapi import APIRouter

from freshroute import config
from freshroute.api import deps
from freshroute.api.schemas import HealthResponse
from freshroute.api.services import outputs as out
from freshroute.config import API_VERSION, SCHEMA_VERSION

router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> HealthResponse:
    return HealthResponse(status="ok", schema_version=SCHEMA_VERSION, api_version=API_VERSION)


@router.get("/config")
def config_constants() -> dict:
    """config.py public UPPERCASE constants, verbatim (costmodel.py has none: its coefficients
    come from scenario tables)."""
    res = {}
    for k in sorted(vars(config)):
        if k.isupper() and not k.startswith("_"):
            try:
                json.dumps(v := getattr(config, k))
            except TypeError:
                continue
            res[k] = v
    return res


@router.get("/scenarios")
def scenarios() -> list[dict]:
    return out.scenario_list()


@router.get("/scenarios/{name}/geo")
def geo(name: str) -> list[dict]:
    p = deps.SCENARIOS / deps.segment(name) / "geo.csv"
    if not p.is_file():
        raise deps.NotFound(f"no geo.csv for scenario {name!r}")
    return out.records(p)["records"]
