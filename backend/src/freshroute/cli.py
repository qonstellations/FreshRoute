"""CLI entry points (ARCHITECTURE.md section 17): `run` = plan -> discounts -> simulate ->
validate -> metrics -> outputs/<run_id>/ (DATABASE.md section 5)."""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

import pandas as pd

from freshroute import dispatch_sheet, reasons
from freshroute import metrics as M
from freshroute.config import (
    DEFAULT_SEED,
    DEMO_SCENARIO,
    DEMO_SEED,
    MC_N,
    MC_N_FALLBACK,
    OVERSHIP_SLACK,
    SCHEMA_VERSION,
)
from freshroute.discount import COLUMNS as DISCOUNT_COLUMNS
from freshroute.io import load_scenario
from freshroute.simulator import simulate
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
    if name == "fifo":
        from freshroute.policies.fifo import FifoPolicy
        return FifoPolicy()
    if name == "fefo":
        from freshroute.policies.fefo import FefoPolicy
        return FefoPolicy()
    if name == "last_day_50":
        from freshroute.policies.last_day_50 import LastDay50Policy
        return LastDay50Policy()
    if name == "milp":
        from freshroute.policies.milp import MilpPolicy
        return MilpPolicy()
    if name == "milp_markdown":
        from freshroute.policies.milp import MilpMarkdownPolicy
        return MilpMarkdownPolicy()
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
    run_id = f"{sc.name}__{policy}__s{seed}" + ("__nv" if newsvendor else "")
    out_dir = Path(out) if out else Path("outputs") / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    ctx = {"seed": seed}
    if newsvendor:
        from freshroute import newsvendor as nv
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


def format_kpis(m: dict) -> str:
    k = m["kpis"]
    return (f"run {m['run_id']}\n"
            f"  spoilage     : {k['spoilage_kg']:.2f} kg ({k['spoilage_pct']:.2f} %)\n"
            f"  fulfillment  : {k['demand_fulfillment_pct']:.2f} %\n"
            f"  net          : INR {k['net_inr']:,.2f}\n"
            f"  violations   : {k['violations']}")


def demo(scenario: str, seed: int, out: str | None = None, with_sensitivity: bool = False) -> int:
    """`freshroute demo`: the ladder (every policy + ladder.json/waterfall.json) for the demo
    scenario, optionally sensitivity; prints the scoreboard and wall time. Returns the
    milp_markdown plan's validator violation count (non-zero exit when > 0)."""
    from freshroute.ladder import PLAN, format_ladder, run_ladder
    t0 = time.perf_counter()
    lad_dir = run_ladder(scenario, seed, out)
    print(format_ladder(lad_dir))
    lad = json.loads((lad_dir / "ladder.json").read_text(encoding="utf-8"))
    if with_sensitivity:  # ponytail: off by default, slow (minutes on practice)
        from freshroute.sensitivity import run_sensitivity
        sen = run_sensitivity(scenario, seed,
                              str(lad_dir.parent / f"{lad['scenario']}__sensitivity__s{seed}"))
        print((sen / "sensitivity.csv").read_text(encoding="utf-8"), end="")
    viol = next(e["kpis"]["violations"] for e in lad["ladder"] if e["policy"] == PLAN)
    print(f"\n{PLAN} validation: {viol} violation(s)")
    print(f"wrote {lad_dir.parent}  ({time.perf_counter() - t0:.1f} s wall)")
    return viol


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="freshroute")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="run a policy on a scenario")
    r.add_argument("--scenario", required=True)
    r.add_argument("--policy", required=True, choices=POLICY_CHOICES)
    r.add_argument("--seed", type=int, default=DEFAULT_SEED)
    r.add_argument("--out")
    r.add_argument("--newsvendor", action="store_true", help="MILP demand cap = newsvendor target")
    r.add_argument("--fail-on-violations", action="store_true", help="exit 1 if violations > 0")
    lad = sub.add_parser("ladder", help="fifo -> fefo -> milp -> milp_markdown + waterfall")
    lad.add_argument("--scenario", required=True)
    lad.add_argument("--seed", type=int, default=DEFAULT_SEED)
    lad.add_argument("--out")
    lad.add_argument("--newsvendor", action="store_true", help="add the newsvendor ablation row")
    sen = sub.add_parser("sensitivity", help="one-at-a-time sensitivity -> sensitivity.csv")
    sen.add_argument("--scenario", required=True)
    sen.add_argument("--seed", type=int, default=DEFAULT_SEED)
    sen.add_argument("--out")
    st = sub.add_parser("stress", help="Monte Carlo bands -> stress.csv, stress_summary.json")
    st.add_argument("--scenario", required=True)
    st.add_argument("--policy", default="milp_markdown", choices=POLICY_CHOICES)
    st.add_argument("--n", type=int, default=MC_N, help=f"realizations (fallback {MC_N_FALLBACK})")
    st.add_argument("--seed", type=int, default=DEFAULT_SEED)
    st.add_argument("--named", action="store_true",
                    help="last-resort fallback: 3 named scenarios (optimistic/base/stress)")
    st.add_argument("--out")
    gn = sub.add_parser("generate", help="regenerate the committed synthetic scenarios")
    gn.add_argument("names", nargs="*", help="scenario names (default: all)")
    gn.add_argument("--out", default="data/scenarios")
    dm = sub.add_parser("demo", help="ladder + waterfall on the demo scenario; the pitch numbers")
    dm.add_argument("--scenario", default=DEMO_SCENARIO)
    dm.add_argument("--seed", type=int, default=DEMO_SEED)
    dm.add_argument("--out")
    dm.add_argument("--with-sensitivity", action="store_true", help="also sensitivity.csv (slow)")
    rp = sub.add_parser("replan", help="replan a run for one event -> <run>/replan/<event_id>/")
    rp.add_argument("--run", required=True, help="run dir (or a replan dir, to chain events)")
    rp.add_argument("--event", required=True, help="event JSON (DATABASE.md section 6)")
    rp.add_argument("--scenario", help="with --policy: create --run first if it has no plan")
    rp.add_argument("--policy", choices=POLICIES)
    rp.add_argument("--seed", type=int, default=DEFAULT_SEED)
    rp.add_argument("--out")
    a = p.parse_args(argv)
    if a.cmd == "replan":
        from freshroute.replan import replan_run
        t0 = time.perf_counter()
        if not (Path(a.run) / "plan.csv").exists():
            if not (a.scenario and a.policy):
                raise SystemExit(f"{a.run} has no plan.csv; pass --scenario and --policy")
            run(a.scenario, a.policy, a.seed, a.run)
            t0 = time.perf_counter()  # the replan time excludes the base run
        out = replan_run(a.run, a.event, a.out)
        d = json.loads((out / "diff.json").read_text(encoding="utf-8"))
        v = json.loads((out / "validation.json").read_text(encoding="utf-8"))
        print(f"replan {d['event_id']} at h {d['at_h']:g}: {d['frozen_shipments']} frozen, "
              f"{len(d['moved_batches'])} batches moved, {v['violation_total']} violation(s)")
        for k, x in d["delta_kpis"].items():
            print(f"  {k:<24}{d['kpis_old_plan_under_event'][k]:>16,.2f} -> "
                  f"{d['kpis_replanned'][k]:>16,.2f}  ({x:+,.2f})")
        print(f"wrote {out}  ({time.perf_counter() - t0:.2f} s wall)")
        if v["violation_total"]:
            sys.exit(1)
        return
    if a.cmd == "generate":
        from freshroute.generator import COMMITTED, generate_committed
        for n in a.names or COMMITTED:
            print(f"wrote {generate_committed(n, a.out)}")
        return
    if a.cmd == "demo":
        if demo(a.scenario, a.seed, a.out, a.with_sensitivity):
            sys.exit(1)
        return
    if a.cmd == "sensitivity":
        from freshroute.sensitivity import run_sensitivity
        out = run_sensitivity(a.scenario, a.seed, a.out)
        print((out / "sensitivity.csv").read_text(encoding="utf-8"), end="")
        print(f"wrote {out}")
        return
    if a.cmd == "stress":
        from freshroute.stress import run_stress
        t0 = time.perf_counter()
        out = run_stress(a.scenario, a.policy, a.n, a.seed, a.out, a.named)
        print((out / "stress_summary.json").read_text(encoding="utf-8"), end="")
        print(f"wrote {out}  ({time.perf_counter() - t0:.1f} s wall)")
        return
    if a.cmd == "ladder":
        from freshroute.ladder import format_ladder, run_ladder
        out = run_ladder(a.scenario, a.seed, a.out, a.newsvendor)
        print(format_ladder(out))
        print(f"wrote {out}")
        return
    out = run(a.scenario, a.policy, a.seed, a.out, a.newsvendor)
    m = json.loads((out / "metrics.json").read_text(encoding="utf-8"))
    print(format_kpis(m))
    print(f"wrote {out}")
    if a.fail_on_violations and m["kpis"]["violations"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
