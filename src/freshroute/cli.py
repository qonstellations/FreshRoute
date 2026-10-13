"""CLI entry points (ARCHITECTURE.md section 17). Only `run` exists, as a stub (S-03)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from freshroute.config import DEFAULT_SEED, SCHEMA_VERSION
from freshroute.io import load_scenario


def run(scenario: str, policy: str, seed: int, out: str | None = None) -> Path:
    """Load the scenario and write a stub metrics.json (all KPIs zero) to the run dir."""
    sc = load_scenario(scenario)
    run_id = f"{sc.name}__{policy}__s{seed}"
    out_dir = Path(out) if out else Path("outputs") / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    metrics = {
        "schema_version": SCHEMA_VERSION, "run_id": run_id, "scenario": str(scenario),
        "policy": policy, "seed": seed, "realization": "base", "stub": True,
        "kpis": {
            "spoilage_kg": 0.0, "spoilage_pct": 0.0, "demand_fulfillment_pct": 0.0,
            "min_dest_fill_pct": 0.0, "net_inr": 0.0, "violations": 0,
        },
    }
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    return out_dir


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="freshroute")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="run a policy on a scenario (stub)")
    r.add_argument("--scenario", required=True)
    r.add_argument("--policy", required=True)
    r.add_argument("--seed", type=int, default=DEFAULT_SEED)
    r.add_argument("--out")
    a = p.parse_args(argv)
    print(f"wrote {run(a.scenario, a.policy, a.seed, a.out) / 'metrics.json'}")


if __name__ == "__main__":
    main()
