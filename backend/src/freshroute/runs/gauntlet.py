"""Hidden-scenario gauntlet (ARCHITECTURE.md section 22): run the MILP on every
data/scenarios/hidden_* and write outputs/gauntlet/gauntlet.csv. Measurements on this machine.

    python -m freshroute.runs.gauntlet [--seed 42] [--out outputs/gauntlet]
"""
from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path

from freshroute.config import DEFAULT_SEED
from freshroute.runs.runner import run as run_policy

SCENARIOS = "data/scenarios"
COLUMNS = ["scenario", "wall_s", "fallback_used", "violations", "net_inr", "spoilage_kg",
           "demand_fulfillment_pct"]


def run(seed: int = DEFAULT_SEED, out: str = "outputs/gauntlet",
        root: str = SCENARIOS) -> list[dict]:
    rows = []
    for sc in sorted(Path(root).glob("hidden_*")):
        t0 = time.perf_counter()
        d = run_policy(str(sc), "milp", seed, out=str(Path(out) / sc.name))
        wall = time.perf_counter() - t0
        k = json.loads((d / "metrics.json").read_text(encoding="utf-8"))["kpis"]
        man = json.loads((d / "run_manifest.json").read_text(encoding="utf-8"))
        solver = man.get("solver") or {}
        rows.append({"scenario": sc.name, "wall_s": round(wall, 1),
                     "fallback_used": solver.get("fallback_used"), "violations": k["violations"],
                     "net_inr": round(k["net_inr"]), "spoilage_kg": round(k["spoilage_kg"]),
                     "demand_fulfillment_pct": round(k["demand_fulfillment_pct"], 1)})
        print(rows[-1])
    Path(out).mkdir(parents=True, exist_ok=True)
    with open(Path(out) / "gauntlet.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, COLUMNS)
        w.writeheader()
        w.writerows(rows)
    return rows


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="freshroute.runs.gauntlet")
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("--out", default="outputs/gauntlet")
    a = p.parse_args(argv)
    run(a.seed, a.out)


if __name__ == "__main__":
    main()
