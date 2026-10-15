"""Single-run orchestration (ARCHITECTURE.md section 17): plan -> discounts -> simulate ->
validate -> metrics -> outputs/<run_id>/ (DATABASE.md section 5)."""
from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import time
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

import pandas as pd

from freshroute.config import OVERSHIP_SLACK, SCHEMA_VERSION
from freshroute.data.io import load_scenario
from freshroute.domain.discount import COLUMNS as DISCOUNT_COLUMNS
from freshroute.engine import discount_advice, dispatch_sheet, reasons
from freshroute.engine import metrics as M
from freshroute.engine.simulator import simulate
from freshroute.policies import REGISTRY, get_policy
from freshroute.runs import naming
from freshroute.runs.progress import Progressive
from validator.validate import validate

POLICIES = ("fifo", "fefo", "last_day_50", "milp", "milp_robust")
NEWSVENDOR_POLICIES = ("milp",)
# Recognised names that cannot run yet. Listed in --policy choices so the parser accepts them
# and _policy() can explain the block, instead of argparse saying "invalid choice".
BLOCKED_POLICIES = ("organizer_baseline",)
POLICY_CHOICES = POLICIES + BLOCKED_POLICIES
ORGANIZER_BASELINE_BLOCKED = (  # also the API's 400 detail (DATABASE.md section 11.2)
    "policy 'organizer_baseline' is not implemented: it waits for the organizers' published "
    "baseline procedure and submission format (README, organizer mapping). "
    f"Available policies: {', '.join(POLICIES)}"
)


def _policy(name: str):
    if name in REGISTRY:
        return get_policy(name)
    if name == "organizer_baseline":
        # Implement this only from the organizers' published procedure. Inventing one and
        # calling it official is the failure AGENTS.md rule 1 exists to prevent.
        raise SystemExit(ORGANIZER_BASELINE_BLOCKED)
    raise SystemExit(f"unknown policy {name!r}; available: {', '.join(POLICIES)}")


def _sha(scenario_dir: Path) -> str:
    h = hashlib.sha256()
    for f in sorted(scenario_dir.glob("*.csv")) + [scenario_dir / "scenario.json"]:
        h.update(f.name.encode() + f.read_bytes())
    return h.hexdigest()


def _git_sha() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                              check=True).stdout.strip()
    except Exception:  # not a git checkout
        return ""


def _versions() -> dict:
    out = {"python": platform.python_version()}
    for p in ("scipy", "pulp", "highspy", "pandas"):
        try:
            out[p] = metadata.version(p)
        except metadata.PackageNotFoundError:
            out[p] = ""
    return out


class _Scored:
    """One scored plan: everything a run directory is written from."""

    def __init__(self, result, discounts, report, sim, metrics) -> None:
        self.result, self.discounts, self.report, self.sim, self.metrics = (
            result, discounts, report, sim, metrics)
        self.net_inr = metrics["kpis"]["net_inr"]


def _score(sc, result, run_id: str, policy: str, seed: int) -> _Scored:
    markdown = result.discounts is not None
    discounts = result.discounts if markdown else pd.DataFrame(columns=list(DISCOUNT_COLUMNS))
    report = validate(sc, result.plan, discounts, overship_slack=OVERSHIP_SLACK)
    sim = simulate(sc, result.plan, discounts)
    sim.update(run_id=run_id, policy=policy, seed=seed, violations=report.violation_total)
    return _Scored(result, discounts, report, sim, M.compute(sc, result.plan, discounts, sim))


def _put(path: Path, write) -> None:
    """Write via a temp file and rename, so a reader never sees a half-written file."""
    tmp = path.with_name(path.name + ".tmp")
    write(tmp)
    for attempt in range(5):  # Windows refuses to replace a file a reader has open
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            if attempt == 4:
                raise
            time.sleep(0.05)


def _write(out_dir: Path, sc, scored: _Scored, manifest: dict) -> None:
    r, d = scored.result, scored.discounts
    sheet, sheet_txt = dispatch_sheet.build(sc, r.plan, r.trips)
    text = lambda t: (lambda f: f.write_text(t, encoding="utf-8"))  # noqa: E731
    csv = lambda df: (lambda f: df.to_csv(f, index=False))  # noqa: E731
    for name, w in (
            ("plan.csv", csv(r.plan)), ("trips.csv", csv(r.trips)),
            ("dispatch_sheet.csv", csv(sheet)), ("dispatch_sheet.txt", text(sheet_txt)),
            ("reason_cards.json", text(json.dumps(
                reasons.build_cards(sc, r.plan, d), indent=2) + "\n")),
            ("discounts.csv", csv(d)), ("sim_ledger.csv", csv(scored.sim["ledger"])),
            ("sim_lots.csv", csv(scored.sim["lots"])),
            ("discount_advice.json", text(json.dumps(
                discount_advice.advise(sc, scored.sim), indent=2) + "\n")),
            ("validation.json", scored.report.write),
            ("run_manifest.json", text(json.dumps(manifest, indent=2) + "\n")),
            ("metrics.json", text(json.dumps(scored.metrics, indent=2) + "\n"))):
        _put(out_dir / name, w)  # metrics.json last: it is what marks the run as present


def run(scenario: str, policy: str, seed: int, out: str | None = None,
        newsvendor: bool = False, on_progress=None) -> Path:
    """Run one policy end to end and write the run directory; returns it. `newsvendor` swaps
    the MILP demand cap for the section 14.3 target (MILP policies only). With `on_progress`
    (MILP policies) the run directory is also written while the solver is still improving, and
    `on_progress({version, net_inr, elapsed_s, final})` fires per published version."""
    if newsvendor and policy not in NEWSVENDOR_POLICIES:
        raise SystemExit(f"--newsvendor needs a MILP policy: {', '.join(NEWSVENDOR_POLICIES)}")
    sc = load_scenario(scenario)
    run_id = naming.run_id(sc.name, policy, seed, newsvendor)
    out_dir = Path(out) if out else Path("outputs") / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    ctx = {"seed": seed}
    if newsvendor:
        from freshroute.engine import newsvendor as nv
        target = nv.demand_target(sc)
        target.to_csv(out_dir / "demand_target.csv", index=False)
        ctx["demand_cap_override"] = nv.override(target)

    def manifest(scored: _Scored, solver) -> dict:
        return {
            "schema_version": SCHEMA_VERSION, "run_id": run_id, "git_sha": _git_sha(),
            "scenario": str(scenario), "scenario_sha256": _sha(Path(scenario)),
            "policy": policy,
            "flags": {"markdown": scored.result.discounts is not None, "newsvendor": newsvendor},
            "seed": seed, "realization": "base", "package_versions": _versions(),
            "solver": solver, "timestamp_utc": datetime.now(timezone.utc).isoformat(
                timespec="seconds")}

    prog = None
    if on_progress is not None and policy in NEWSVENDOR_POLICIES:
        prog = Progressive(
            lambda res: _score(sc, res, run_id, policy, seed),
            lambda b: _write(out_dir, sc, b, manifest(b, {"status": "incumbent", "final": False})),
            on_progress)
        ctx["on_plan"] = prog.offer
    try:
        result = _policy(policy).plan(sc, ctx)
    finally:
        if prog is not None:
            prog.close()
    scored = _score(sc, result, run_id, policy, seed)
    if prog is None:
        _write(out_dir, sc, scored, manifest(scored, result.solver))
    else:
        prog._publish = lambda b: _write(out_dir, sc, b, manifest(b, result.solver))
        prog.finish(scored)
    if not newsvendor:  # keep an existing ladder on the latest run of each policy (A-55)
        from freshroute.runs.ladder import refresh_ladder  # lazy: ladder imports this module
        refresh_ladder(out_dir, sc.name, policy, seed)
    return out_dir
