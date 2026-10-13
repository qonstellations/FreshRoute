"""C-09 perf harness (ARCHITECTURE.md section 22): generate a scale x practice-sized
SYNTHETIC scenario and time `build_arcs` and `MilpPolicy().plan`. Numbers printed and
written to perf.json are measurements on this machine, not claims.

    python -m freshroute.perf [--scale 10] [--seed 42] [--out outputs/perf]
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from freshroute.config import DEFAULT_SEED
from freshroute.feasibility import build_arcs
from freshroute.generator import generate
from freshroute.io import load_scenario
from freshroute.policies.milp import MilpPolicy

BASE = "data/scenarios/practice"


def run(scale: int = 10, seed: int = DEFAULT_SEED, out: str = "outputs/perf",
        base: str = BASE) -> dict:
    """Generate the scaled scenario under <out>/scenario, time it, write <out>/perf.json."""
    b = load_scenario(base)
    t, meta = b.tables, b.meta
    # ponytail: batches and fleet scale together so capacity keeps pace with supply;
    # destinations and horizon stay at the base size.
    size = {"n_batches": len(t["batches"]) * scale, "n_dests": len(t["destinations"]),
            "days": int(meta["horizon_days"]), "n_vehicles": len(t["vehicles"]) * scale}
    out_dir = Path(out)
    sc = load_scenario(generate(f"perf_x{scale}", seed, **size, out_dir=out_dir / "scenario"))

    t0 = time.perf_counter()
    arcs = build_arcs(sc)
    arcs_s = time.perf_counter() - t0
    t0 = time.perf_counter()
    solver = MilpPolicy().plan(sc, {"seed": seed}).solver
    plan_s = time.perf_counter() - t0

    res = {"scale": scale, "seed": seed, **size, "arcs_total": len(arcs),
           "arcs_feasible": int(arcs.feasible.sum()), "status": solver.get("status"),
           "fallback_used": solver.get("fallback_used"),
           "solve_seconds": round(solver.get("solve_seconds", 0.0), 3),
           "build_arcs_seconds": round(arcs_s, 3), "plan_seconds": round(plan_s, 3)}
    (out_dir / "perf.json").write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
    return res


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="freshroute.perf")
    p.add_argument("--scale", type=int, default=10)
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("--out", default="outputs/perf")
    a = p.parse_args(argv)
    res = run(a.scale, a.seed, a.out)
    for k, v in res.items():
        print(f"  {k:<20}: {v}")
    print(f"wrote {Path(a.out) / 'perf.json'}")


if __name__ == "__main__":
    main()
