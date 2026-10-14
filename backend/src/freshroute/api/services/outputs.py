"""Reading files under outputs/ and data/scenarios/ (ARCHITECTURE.md section 16)."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from freshroute.api import deps
from freshroute.runs.naming import run_id as name  # noqa: F401  (the one naming function)


def out_dir(scenario: str, kind: str, seed: int) -> Path:
    return deps.outputs() / deps.segment(name(scenario, kind, seed))


def run_dir(run_id: str) -> Path:
    d = deps.outputs() / deps.segment(run_id)
    if not (d / "metrics.json").is_file():
        raise deps.NotFound(f"run {run_id!r} not found")
    return d


def records(path: Path) -> dict:
    """CSV as {columns, records}; +-inf become null so the JSON is valid."""
    df = pd.read_csv(path).replace([float("inf"), float("-inf")], float("nan"))
    return {"columns": list(df.columns),
            "records": df.astype(object).where(df.notna(), None).to_dict(orient="records")}


def scenario_list() -> list[dict]:
    out = []
    for p in sorted(deps.SCENARIOS.glob("*/scenario.json")):
        m = json.loads(p.read_text(encoding="utf-8"))
        out.append({k: m.get(k) for k in ("name", "source", "horizon_days", "window_mode")})
    return sorted(out, key=lambda s: str(s["name"]))
