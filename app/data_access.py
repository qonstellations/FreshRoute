"""Read-only access to run outputs for the dashboard (ARCHITECTURE §16, DATABASE §5.14).

The app never computes a KPI; it only loads what the pipeline wrote.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUTS = ROOT / "outputs"
FIXTURE = ROOT / "tests" / "fixtures" / "metrics_example.json"


def list_runs(outputs: Path = OUTPUTS) -> list[str]:
    """Run ids (dirs containing metrics.json), sorted."""
    if not outputs.is_dir():
        return []
    return sorted(p.name for p in outputs.iterdir() if (p / "metrics.json").is_file())


def load_metrics(run_id: str | None = None, outputs: Path = OUTPUTS) -> tuple[dict, bool]:
    """Return (metrics, is_fixture). Falls back to the example fixture when no run exists."""
    if run_id is None:
        runs = list_runs(outputs)
        run_id = runs[0] if runs else None
    if run_id is None:
        return json.loads(FIXTURE.read_text(encoding="utf-8")), True
    return json.loads((outputs / run_id / "metrics.json").read_text(encoding="utf-8")), False
