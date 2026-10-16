"""Run queue: worker threads, file-backed state (ARCHITECTURE.md section 16.1, D-21,
DATABASE.md section 11.3)."""
from __future__ import annotations

import json
import logging
import os
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from freshroute.config import API_VERSION, JOB_WORKERS, REPLAN_WORKERS

log = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def job_path(outputs: Path, run_id: str) -> Path:
    return outputs / ".api" / "jobs" / f"{run_id}.json"


def read_job(outputs: Path, run_id: str) -> dict | None:
    p = job_path(outputs, run_id)
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None


def _write(outputs: Path, job: dict) -> None:
    try:
        p = job_path(outputs, job["run_id"])
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(job, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, p)
    except OSError as e:
        log.warning("cannot write job state to %s: %s", outputs, e)


class JobQueue:
    """Two lanes, one registry (D-21, D-37): long jobs (runs, stress, frontier) are serialized
    on one worker; short jobs (re-plans) have their own so they never wait behind a long solve."""

    def __init__(self, workers: int = JOB_WORKERS, short_workers: int = REPLAN_WORKERS) -> None:
        self._executor = ThreadPoolExecutor(max_workers=workers)
        self._short = ThreadPoolExecutor(max_workers=short_workers)
        self._live: set[str] = set()  # job ids queued or running in this process
        self._lock = threading.Lock()

    def is_live(self, job_id: str, prefix: bool = False) -> bool:
        """`job_id` (or, with prefix, any id starting with it) is queued or running here."""
        with self._lock:
            return any(j == job_id or (prefix and j.startswith(job_id)) for j in self._live)

    def live_job(self, outputs: Path, job_id: str) -> dict | None:
        """The job record if it runs in this process; a "running" file left by a previous
        server process is stale and returns None."""
        with self._lock:
            live = job_id in self._live
        job = read_job(outputs, job_id) if live else None
        return job if job and job["state"] == "running" else None

    def submit_if_idle(self, outputs: Path, job_id: str, fn, done_file: Path, short: bool = False,
                       **meta) -> dict:
        """Atomically: return the live job for `job_id`, else write the running state and
        enqueue `fn` (on the short lane when `short`). The job is done when `done_file` exists."""
        with self._lock:
            if job_id in self._live:
                existing = read_job(outputs, job_id)
                if existing:
                    return existing
            job = {"api_version": API_VERSION, "run_id": job_id, "state": "running", **meta,
                   "started_utc": _now(), "finished_utc": None, "error": None}
            _write(outputs, job)
            self._live.add(job_id)
            lane = self._short if short else self._executor
            lane.submit(self._work, outputs, dict(job), fn, done_file)
            return job

    def update(self, outputs: Path, job_id: str, **fields) -> None:
        """Merge fields (e.g. `progress`) into a live job's record."""
        with self._lock:
            job = read_job(outputs, job_id)
            if job and job["state"] == "running":
                _write(outputs, {**job, **fields})

    def _work(self, outputs: Path, job: dict, fn, done_file: Path) -> None:
        try:
            fn()
            ok = done_file.is_file()
            job.update(state="done" if ok else "error",
                       error=None if ok else f"no {done_file.name}")
        except (Exception, SystemExit) as e:  # a failed job is state error, never a crash
            log.exception("job %s failed", job["run_id"])
            job.update(state="error", error=str(e) or type(e).__name__,
                       traceback=traceback.format_exc())
        cur = read_job(outputs, job["run_id"]) or {}
        if cur.get("progress"):  # keep the last progress the run reported
            job["progress"] = cur["progress"]
        job["finished_utc"] = _now()
        _write(outputs, job)
        with self._lock:
            self._live.discard(job["run_id"])


queue = JobQueue()
