"""Shared API plumbing: paths, path guards, error types (ARCHITECTURE.md section 16)."""
from __future__ import annotations

import re
from pathlib import Path, PureWindowsPath

from freshroute.api import data_access as da

ROOT = da.ROOT
SCENARIOS = ROOT / "data" / "scenarios"


class NotFound(Exception):
    """Mapped to HTTP 404 in app.py."""


class BadRequest(Exception):
    """Mapped to HTTP 400 in app.py."""


def outputs() -> Path:
    """Read at call time so tests can monkeypatch `data_access.OUTPUTS`."""
    return da.OUTPUTS


def segment(name: str) -> str:
    """Reject anything that is not a single path segment (no traversal out of outputs/)."""
    if name in ("", ".", "..") or any(c in name for c in "/\\:"):
        raise NotFound(f"not found: {name!r}")
    return name


def scenario_path(scenario: str) -> str:
    """A bare scenario name resolves under data/scenarios/; a relative path resolves against
    the repo root. Absolute paths and `..` are rejected (400)."""
    if (not any(c in scenario for c in "/\\:") and scenario not in ("", ".", "..")
            and (SCENARIOS / scenario).is_dir()):
        return str(SCENARIOS / scenario)
    win = PureWindowsPath(scenario)
    if (scenario.startswith(("/", "\\")) or win.is_absolute() or win.drive
            or ".." in re.split(r"[\\/]", scenario)):
        raise BadRequest(f"scenario {scenario!r}: absolute paths and '..' are not allowed")
    return str(ROOT / scenario)
