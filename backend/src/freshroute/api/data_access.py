"""Read-only access to run outputs for the dashboard (ARCHITECTURE §16, DATABASE §5.14).

The API never computes a KPI; it only loads what the pipeline wrote.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from freshroute.runs.naming import run_id

ROOT = Path(__file__).resolve().parents[4]  # backend/src/freshroute/api/ -> repo root


def _is_writable(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        test = path / ".write_test"
        test.touch()
        test.unlink()
        return True
    except OSError:
        return False


def _resolve_outputs() -> Path:
    env = os.getenv("FRESHROUTE_OUTPUTS")
    if env:
        p = Path(env)
        p.mkdir(parents=True, exist_ok=True)
        return p
    p = ROOT / "outputs"
    backup = p / "demo_backup"
    if _is_writable(p):
        # Fresh clone: no runs yet, so serve the committed demo runs.
        if not any(p.glob("*/metrics.json")):
            _seed(backup, p)
        return p

    # Read-only repo (Vercel Function): serve the committed demo runs in place.
    # ponytail: no /tmp copy; live solves are unavailable here anyway.
    return backup if backup.is_dir() else p


def _seed(src: Path, dst: Path) -> None:
    """Copy demo runs into a writable outputs dir; best-effort, never crash the import."""
    if not src.is_dir():
        return
    import shutil

    for item in src.iterdir():
        target = dst / item.name
        try:
            if item.is_dir() and not target.exists():
                shutil.copytree(item, target)
            elif item.is_file() and not target.exists():
                shutil.copy2(item, target)
        except OSError:
            continue


OUTPUTS = _resolve_outputs()
FIXTURE = ROOT / "backend" / "tests" / "fixtures" / "metrics_example.json"


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


def read_json(path: Path) -> dict | None:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def load_validation(run_id: str | None, outputs: Path = OUTPUTS) -> dict | None:
    """validation.json (DATABASE §5.8) for a run, or None."""
    return read_json(outputs / run_id / "validation.json") if run_id else None


def load_manifest(run_id: str | None, outputs: Path = OUTPUTS) -> dict | None:
    """run_manifest.json (DATABASE §5.1) for a run, or None."""
    return read_json(outputs / run_id / "run_manifest.json") if run_id else None


def load_ladder(scenario: str, seed: int, outputs: Path = OUTPUTS) -> dict | None:
    """ladder.json (DATABASE §5.11) at outputs/<scenario>__ladder__s<seed>/, or None."""
    return read_json(outputs / run_id(scenario, "ladder", seed) / "ladder.json")


def load_baseline(scenario: str, seed: int, outputs: Path = OUTPUTS) -> dict | None:
    """Baseline as {"policy", "kpis", "source"}, or None when nothing is on disk.

    Order: ladder official_baseline (when not null) -> ladder "fefo" entry ->
    sibling run <scenario>__fefo__s<seed>/metrics.json.
    """
    ladder = load_ladder(scenario, seed, outputs)
    if ladder:
        if ladder.get("official_baseline"):
            return {**ladder["official_baseline"], "source": "ladder"}
        for e in ladder.get("ladder", []):
            if e.get("policy") == "fefo":
                return {**e, "source": "ladder"}
    m = read_json(outputs / run_id(scenario, "fefo", seed) / "metrics.json")
    return {"policy": "fefo", "kpis": m["kpis"], "source": "run"} if m else None
