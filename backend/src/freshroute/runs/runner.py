"""Single-run orchestration (ARCHITECTURE.md section 17): plan -> discounts -> simulate ->
validate -> metrics -> outputs/<run_id>/ (DATABASE.md section 5)."""
from __future__ import annotations

import hashlib
import json
import platform
import subprocess
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

import pandas as pd

from freshroute.config import OVERSHIP_SLACK, SCHEMA_VERSION
from freshroute.data.io import load_scenario
from freshroute.domain.discount import COLUMNS as DISCOUNT_COLUMNS
from freshroute.engine import dispatch_sheet, reasons
from freshroute.engine import metrics as M
from freshroute.engine.simulator import simulate
from freshroute.policies import REGISTRY, get_policy
from freshroute.runs import naming
from validator.validate import validate

POLICIES = ("fifo", "fefo", "last_day_50", "milp", "milp_markdown")
NEWSVENDOR_POLICIES = ("milp", "milp_markdown")
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


def run(scenario: str, policy: str, seed: int, out: str | None = None,
        newsvendor: bool = False) -> Path:
    """Run one policy end to end and write the run directory; returns it. `newsvendor` swaps
    the MILP demand cap for the section 14.3 target (MILP policies only)."""
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
    result = _policy(policy).plan(sc, ctx)
    plan, trips = result.plan, result.trips
    markdown = result.discounts is not None
    discounts = result.discounts if markdown else pd.DataFrame(columns=list(DISCOUNT_COLUMNS))
    report = validate(sc, plan, discounts, overship_slack=OVERSHIP_SLACK)
    sim = simulate(sc, plan, discounts)
    sim.update(run_id=run_id, policy=policy, seed=seed, violations=report.violation_total)
    metrics = M.compute(sc, plan, discounts, sim)

    plan.to_csv(out_dir / "plan.csv", index=False)
    trips.to_csv(out_dir / "trips.csv", index=False)
    sheet, sheet_txt = dispatch_sheet.build(sc, plan, trips)
    sheet.to_csv(out_dir / "dispatch_sheet.csv", index=False)
    (out_dir / "dispatch_sheet.txt").write_text(sheet_txt, encoding="utf-8")
    (out_dir / "reason_cards.json").write_text(
        json.dumps(reasons.build_cards(sc, plan, discounts), indent=2) + "\n", encoding="utf-8")
    discounts.to_csv(out_dir / "discounts.csv", index=False)
    sim["ledger"].to_csv(out_dir / "sim_ledger.csv", index=False)
    sim["lots"].to_csv(out_dir / "sim_lots.csv", index=False)
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    report.write(out_dir / "validation.json")
    manifest = {
        "schema_version": SCHEMA_VERSION, "run_id": run_id, "git_sha": _git_sha(),
        "scenario": str(scenario), "scenario_sha256": _sha(Path(scenario)), "policy": policy,
        "flags": {"markdown": markdown, "newsvendor": newsvendor}, "seed": seed,
        "realization": "base", "package_versions": _versions(), "solver": result.solver,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    (out_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n",
                                               encoding="utf-8")
    return out_dir
