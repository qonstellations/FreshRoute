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


def _work(outputs: Path, job: dict, fn, done_file: Path) -> None:
    try:
        fn()
        ok = done_file.is_file()
        job.update(state="done" if ok else "error", error=None if ok else f"no {done_file.name}")
    except (Exception, SystemExit) as e:  # a failed job is state error, never a crash
        job.update(state="error", error=str(e) or type(e).__name__)
    job["finished_utc"] = _now()
    _write(outputs, job)


def submit_call(outputs: Path, job_id: str, fn, done_file: Path, **meta) -> dict:
    """Write the running state and enqueue `fn`; the job is done when `done_file` exists."""
    job = {"api_version": API_VERSION, "run_id": job_id, "state": "running", **meta,
           "started_utc": _now(), "finished_utc": None, "error": None}
    _write(outputs, job)
    _executor.submit(_work, outputs, dict(job), fn, done_file)
    return job


def submit(outputs: Path, run_id: str, scenario: str, policy: str, seed: int,
           newsvendor: bool = False) -> dict:
    """Enqueue cli.run; returns the job record."""
    run_dir = outputs / run_id
    return submit_call(outputs, run_id, lambda: cli.run(scenario, policy, seed, str(run_dir),
                                                        newsvendor=newsvendor),
                       run_dir / "metrics.json", scenario=scenario, policy=policy, seed=seed)
