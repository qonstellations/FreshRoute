"""Scenario loading, unit conversion and integrity checks (ARCHITECTURE.md section 6;
DATABASE.md sections 2, 3.10 and 7). The ONLY place *_pct (0-100) becomes *_frac (0-1).
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from freshroute.config import DISPATCH_HOUR, SCHEMA_VERSION
from freshroute.data import schema as S

log = logging.getLogger(__name__)


class ScenarioError(ValueError):
    """Raised when a scenario violates a load-time error rule."""


@dataclass
class Scenario:
    path: Path
    meta: dict
    tables: dict[str, pd.DataFrame]
    warnings: list[str] = field(default_factory=list)

    @property
    def name(self) -> str:
        return self.meta["name"]

    @property
    def dispatch_hour(self) -> float:
        return self.meta.get("dispatch_hour", DISPATCH_HOUR)


def _check_table(name: str, df: pd.DataFrame, errors: list[str]) -> None:
    optional = S.OPTIONAL_COLUMNS.get(name, ())
    cols = S.TABLES.get(name) or S.OPTIONAL_TABLES[name]
    required = [c for c in cols if c not in optional]
    missing = [c for c in required if c not in df.columns]
    if missing:
        errors.append(f"{name}: missing columns {missing}")
        return
    for c in required:
        if df[c].isna().any():
            errors.append(f"{name}.{c}: blank/NaN in required column")
    if df.duplicated(list(S.PKS[name])).any():
        errors.append(f"{name}: duplicate primary key {S.PKS[name]}")
    for (t, c), allowed in S.ENUMS.items():
        if t == name and not df[c].isin(allowed).all():
            errors.append(f"{name}.{c}: values outside {sorted(allowed)}")
    for t, c in S.NONNEG:
        if t == name and (df[c] < 0).any():
            errors.append(f"{name}.{c}: must be >= 0")
    for t, c in S.POSITIVE:
        if t == name and (df[c] <= 0).any():
            errors.append(f"{name}.{c}: must be > 0")
    for t, lo, hi in S.ORDERED:
        if t == name and (df[lo] > df[hi]).any():
            errors.append(f"{name}: {lo} <= {hi} violated")


def _checks(meta: dict, t: dict[str, pd.DataFrame]) -> list[str]:
    """Return warnings; raise ScenarioError on any error (DATABASE.md section 7)."""
    errors: list[str] = []
    for name, df in t.items():
        _check_table(name, df, errors)
    if errors:  # semantic checks need well-formed tables
        raise ScenarioError("; ".join(errors))
    for tab, col, ptab, pcol in S.FKS:
        if not t[tab][col].isin(t[ptab][pcol]).all():
            errors.append(f"FK violation: {tab}.{col} -> {ptab}.{pcol}")
    d, ln = t["destinations"], t["lanes"]
    if (d["window_open_h"] >= d["window_close_h"]).any():
        errors.append("destinations: window_open_h must be < window_close_h")
    if ((ln["mode"] == "rail") & ln["departure_slots"].isna()).any():
        errors.append("lanes: rail lane without departure_slots")
    if errors:
        raise ScenarioError("; ".join(errors))
    warns: list[str] = []
    if meta.get("source") == "synthetic":
        warns.append("scenario.source = synthetic: numbers are NOT real data")
    if not t["batches"]["origin_hub"].isin(ln["origin"]).all():
        warns.append("batch origin_hub with no lane")
    lane_keys = set(zip(ln["origin"], ln["mode"], strict=True))
    veh = t["vehicles"]
    if any(k not in lane_keys for k in zip(veh["origin"], veh["mode"], strict=True)):
        warns.append("vehicle (origin, mode) with no matching lane")
    if ln[ln["mode"] != "rail"]["departure_slots"].notna().any():
        warns.append("non-rail lane with departure_slots")
    return warns


def load_scenario(path: str | Path) -> Scenario:
    """Load `<path>/*.csv` + `scenario.json`, check integrity, convert *_pct to *_frac."""
    path = Path(path)
    meta = json.loads((path / "scenario.json").read_text(encoding="utf-8"))
    if meta.get("schema_version") != SCHEMA_VERSION:
        raise ScenarioError(f"schema_version {meta.get('schema_version')} != {SCHEMA_VERSION}")
    tables: dict[str, pd.DataFrame] = {}
    for name in S.TABLES:
        f = path / f"{name}.csv"
        if not f.exists():
            raise ScenarioError(f"missing table file {f}")
        df = pd.read_csv(f)
        for c in S.OPTIONAL_COLUMNS.get(name, ()):  # optional columns may be absent entirely
            if c not in df.columns:
                df[c] = float("nan")
        tables[name] = df
    h = meta.get("horizon_days")
    if not isinstance(h, int) or isinstance(h, bool) or h < 1:
        raise ScenarioError(f"scenario.json horizon_days must be an integer >= 1, got {h!r}")
    if (path / "geo.csv").exists():
        tables["geo"] = pd.read_csv(path / "geo.csv")
    warns = _checks(meta, tables)
    c = tables["commodities"]
    for pct, frac in S.PCT_TO_FRAC.items():
        c[frac] = c.pop(pct) / 100.0
    for w in warns:
        log.warning(w)
    return Scenario(path=path, meta=meta, tables=tables, warnings=warns)
