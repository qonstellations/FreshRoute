"""CLI entry points (ARCHITECTURE.md section 17): `run` = plan -> discounts -> simulate ->
validate -> metrics -> outputs/<run_id>/ (DATABASE.md section 5)."""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

import pandas as pd
from validator.validate import validate

from freshroute import metrics as M
from freshroute.config import DEFAULT_SEED, OVERSHIP_SLACK, SCHEMA_VERSION
from freshroute.discount import COLUMNS as DISCOUNT_COLUMNS
from freshroute.io import load_scenario
from freshroute.simulator import simulate

POLICIES = ("fifo", "milp")


def _policy(name: str):
    if name == "fifo":
        from freshroute.policies.fifo import FifoPolicy
        return FifoPolicy()
    if name == "milp":
        from freshroute.policies.milp import MilpPolicy
        return MilpPolicy()
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


def run(scenario: str, policy: str, seed: int, out: str | None = None) -> Path:
    """Run one policy end to end and write the run directory; returns it."""
    sc = load_scenario(scenario)
    run_id = f"{sc.name}__{policy}__s{seed}"
    out_dir = Path(out) if out else Path("outputs") / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    result = _policy(policy).plan(sc, {"seed": seed})
    plan, trips = result.plan, result.trips
    # ponytail: no markdown policy yet (fifo/milp are markdown-free per ARCH 12): empty discounts
    discounts = pd.DataFrame(columns=list(DISCOUNT_COLUMNS))
    report = validate(sc, plan, discounts, overship_slack=OVERSHIP_SLACK)
    sim = simulate(sc, plan, discounts)
    sim.update(run_id=run_id, policy=policy, seed=seed, violations=report.violation_total)
    metrics = M.compute(sc, plan, discounts, sim)

    plan.to_csv(out_dir / "plan.csv", index=False)
    trips.to_csv(out_dir / "trips.csv", index=False)
    discounts.to_csv(out_dir / "discounts.csv", index=False)
    sim["ledger"].to_csv(out_dir / "sim_ledger.csv", index=False)
    sim["lots"].to_csv(out_dir / "sim_lots.csv", index=False)
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    report.write(out_dir / "validation.json")
    manifest = {
        "schema_version": SCHEMA_VERSION, "run_id": run_id, "git_sha": _git_sha(),
        "scenario": str(scenario), "scenario_sha256": _sha(Path(scenario)), "policy": policy,
        "flags": {"markdown": False, "newsvendor": False}, "seed": seed,
        "realization": "base", "package_versions": _versions(), "solver": result.solver,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    (out_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n",
                                               encoding="utf-8")
    return out_dir


def format_kpis(m: dict) -> str:
    k = m["kpis"]
    return (f"run {m['run_id']}\n"
            f"  spoilage     : {k['spoilage_kg']:.2f} kg ({k['spoilage_pct']:.2f} %)\n"
            f"  fulfillment  : {k['demand_fulfillment_pct']:.2f} %\n"
            f"  net          : INR {k['net_inr']:,.2f}\n"
            f"  violations   : {k['violations']}")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="freshroute")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="run a policy on a scenario")
    r.add_argument("--scenario", required=True)
    r.add_argument("--policy", required=True, choices=POLICIES)
    r.add_argument("--seed", type=int, default=DEFAULT_SEED)
    r.add_argument("--out")
    r.add_argument("--fail-on-violations", action="store_true", help="exit 1 if violations > 0")
    a = p.parse_args(argv)
    out = run(a.scenario, a.policy, a.seed, a.out)
    m = json.loads((out / "metrics.json").read_text(encoding="utf-8"))
    print(format_kpis(m))
    print(f"wrote {out}")
    if a.fail_on_violations and m["kpis"]["violations"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
