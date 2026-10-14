"""Run queue: one worker thread, file-backed state (ARCHITECTURE.md section 16.1, D-21,
DATABASE.md section 11.3)."""
from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from freshroute import cli
from freshroute.config import API_VERSION, JOB_WORKERS

_executor = ThreadPoolExecutor(max_workers=JOB_WORKERS)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def job_path(outputs: Path, run_id: str) -> Path:
    return outputs / ".api" / "jobs" / f"{run_id}.json"


def read_job(outputs: Path, run_id: str) -> dict | None:
    p = job_path(outputs, run_id)
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None


def _write(outputs: Path, job: dict) -> None:
    p = job_path(outputs, job["run_id"])
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(job, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, p)


def _work(outputs: Path, job: dict) -> None:
    run_dir = outputs / job["run_id"]
    try:
        cli.run(job["scenario"], job["policy"], job["seed"], str(run_dir))
        ok = (run_dir / "metrics.json").is_file()
        job.update(state="done" if ok else "error", error=None if ok else "no metrics.json")
    except (Exception, SystemExit) as e:  # a failed run is a job in state error, never a crash
        job.update(state="error", error=str(e) or type(e).__name__)
    job["finished_utc"] = _now()
    _write(outputs, job)


def submit(outputs: Path, run_id: str, scenario: str, policy: str, seed: int) -> dict:
    """Write the running state and enqueue cli.run; returns the job record."""
    job = {"api_version": API_VERSION, "run_id": run_id, "state": "running",
           "scenario": scenario, "policy": policy, "seed": seed,
           "started_utc": _now(), "finished_utc": None, "error": None}
    _write(outputs, job)
    _executor.submit(_work, outputs, dict(job))
    return job
