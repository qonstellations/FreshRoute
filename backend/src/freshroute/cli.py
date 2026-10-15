"""CLI entry points (ARCHITECTURE.md section 17): argparse + KPI formatting + demo. The
orchestration lives in freshroute.runs; `run` and the policy names are re-exported here."""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from freshroute.config import DEFAULT_SEED, DEMO_SCENARIO, DEMO_SEED, MC_N, MC_N_FALLBACK, PLAN
from freshroute.runs import naming
from freshroute.runs.runner import (  # noqa: F401  (re-exported: API, tests)
    BLOCKED_POLICIES,
    NEWSVENDOR_POLICIES,
    ORGANIZER_BASELINE_BLOCKED,
    POLICIES,
    POLICY_CHOICES,
    _policy,
    run,
)


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
    milp plan's validator violation count (non-zero exit when > 0)."""
    from freshroute.runs.ladder import format_ladder, run_ladder
    t0 = time.perf_counter()
    lad_dir = run_ladder(scenario, seed, out)
    print(format_ladder(lad_dir))
    lad = json.loads((lad_dir / "ladder.json").read_text(encoding="utf-8"))
    if with_sensitivity:  # ponytail: off by default, slow (minutes on practice)
        from freshroute.runs.sensitivity import run_sensitivity
        sen = run_sensitivity(scenario, seed,
                              str(lad_dir.parent
                                  / naming.run_id(lad["scenario"], "sensitivity", seed)))
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
    lad = sub.add_parser("ladder", help="fifo -> fefo -> milp + waterfall")
    lad.add_argument("--scenario", required=True)
    lad.add_argument("--seed", type=int, default=DEFAULT_SEED)
    lad.add_argument("--out")
    lad.add_argument("--newsvendor", action="store_true", help="add the newsvendor ablation row")
    sen = sub.add_parser("sensitivity", help="one-at-a-time sensitivity -> sensitivity.csv")
    sen.add_argument("--scenario", required=True)
    sen.add_argument("--seed", type=int, default=DEFAULT_SEED)
    sen.add_argument("--out")
    fr = sub.add_parser("frontier", help="profit vs spoilage over FRONTIER_LAMBDAS -> frontier.csv")
    fr.add_argument("--scenario", required=True)
    fr.add_argument("--seed", type=int, default=DEFAULT_SEED)
    fr.add_argument("--out")
    st = sub.add_parser("stress", help="Monte Carlo bands -> stress.csv, stress_summary.json")
    st.add_argument("--scenario", required=True)
    st.add_argument("--policy", default="milp", choices=POLICY_CHOICES)
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
        from freshroute.runs.replan import replan_run
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
    if a.cmd == "frontier":
        from freshroute.runs.frontier import run_frontier
        out = run_frontier(a.scenario, a.seed, a.out)
        print((out / "frontier.csv").read_text(encoding="utf-8"), end="")
        return
    if a.cmd == "sensitivity":
        from freshroute.runs.sensitivity import run_sensitivity
        out = run_sensitivity(a.scenario, a.seed, a.out)
        print((out / "sensitivity.csv").read_text(encoding="utf-8"), end="")
        print(f"wrote {out}")
        return
    if a.cmd == "stress":
        from freshroute.runs.stress import run_stress
        t0 = time.perf_counter()
        out = run_stress(a.scenario, a.policy, a.n, a.seed, a.out, a.named)
        print((out / "stress_summary.json").read_text(encoding="utf-8"), end="")
        print(f"wrote {out}  ({time.perf_counter() - t0:.1f} s wall)")
        return
    if a.cmd == "ladder":
        from freshroute.runs.ladder import format_ladder, run_ladder
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
