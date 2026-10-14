"""Attribution ladder and waterfall (ARCHITECTURE.md section 12): runs every ladder policy
through runs.runner.run (one simulator); writes ladder.json + waterfall.json (DATABASE.md 5.11)."""
from __future__ import annotations

import json
from pathlib import Path

from freshroute.config import BASELINE, PLAN
from freshroute.io import load_scenario
from freshroute.runs import naming
from freshroute.runs.runner import run

LADDER = ("fifo", "fefo", "milp", "milp_markdown")
EXTRAS = ("last_day_50",)
TOLERANCE_INR = 0.01
ABLATION_DELTAS = ("net_inr", "spoilage_kg", "spoilage_pct", "demand_fulfillment_pct")


def waterfall(base: dict, plan: dict) -> list[dict]:
    """Steps from two economics_inr dicts (ARCH section 12); deltas sum to net_P - net_B."""
    def d(k: str) -> float:
        return plan[k] - base[k]
    return [
        {"label": "Baseline net", "value": base["net"], "type": "total"},
        {"label": "Spoilage cost avoided", "value": 0.0 - d("spoilage_cost"), "type": "delta"},
        {"label": "Extra sales (list price)", "value": d("gross_revenue_at_list"), "type": "delta"},
        {"label": "Cost of extra goods sold", "value": 0.0 - d("cost_of_goods_sold"),
         "type": "delta"},
        {"label": "Extra transport", "value": 0.0 - d("transport"), "type": "delta"},
        {"label": "Extra handling", "value": 0.0 - d("handling"), "type": "delta"},
        {"label": "Discounts given", "value": 0.0 - d("discount_cost"), "type": "delta"},
        {"label": "FreshRoute net", "value": plan["net"], "type": "total"},
    ]


def run_ladder(scenario: str, seed: int, out: str | None = None,
               newsvendor: bool = False) -> Path:
    """Run ladder + extras policies; write <out or outputs>/<name>__ladder__s<seed>/; return it.
    `newsvendor` adds an `ablation` entry: PLAN re-run with --newsvendor (section 14.3)."""
    root = Path(out) if out else Path("outputs")
    name = load_scenario(scenario).name
    metrics = {}
    for pol in LADDER + EXTRAS:
        run_dir = run(scenario, pol, seed, str(root / naming.run_id(name, pol, seed)))
        metrics[pol] = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))

    out_dir = root / naming.run_id(name, "ladder", seed)
    out_dir.mkdir(parents=True, exist_ok=True)
    ladder = {
        "scenario": name, "seed": seed, "realization": "base",
        "official_baseline": None,  # no organizer baseline procedure published yet
        "ladder": [{"policy": p, "kpis": metrics[p]["kpis"]} for p in LADDER],
        "extras": [{"policy": p, "kpis": metrics[p]["kpis"]} for p in EXTRAS],
    }
    if newsvendor:  # flag off: ladder.json unchanged (AGENTS.md rule 9)
        nv_id = naming.run_id(name, PLAN, seed, True)
        k = json.loads((run(scenario, PLAN, seed, str(root / nv_id), newsvendor=True)
                        / "metrics.json").read_text(encoding="utf-8"))["kpis"]
        ref = metrics[PLAN]["kpis"]
        ladder["ablation"] = [{
            "policy": PLAN, "flags": {"newsvendor": True}, "run_id": nv_id, "vs": PLAN,
            "kpis": k, "delta": {key: k[key] - ref[key] for key in ABLATION_DELTAS}}]
    wf = {"baseline": BASELINE, "plan": PLAN, "tolerance_inr": TOLERANCE_INR,
          "steps": waterfall(metrics[BASELINE]["economics_inr"], metrics[PLAN]["economics_inr"])}
    (out_dir / "ladder.json").write_text(json.dumps(ladder, indent=2) + "\n", encoding="utf-8")
    (out_dir / "waterfall.json").write_text(json.dumps(wf, indent=2) + "\n", encoding="utf-8")
    return out_dir


def format_ladder(out_dir: Path) -> str:
    lad = json.loads((out_dir / "ladder.json").read_text(encoding="utf-8"))
    wf = json.loads((out_dir / "waterfall.json").read_text(encoding="utf-8"))
    lines = [f"{'policy':<14}{'spoil kg':>11}{'spoil %':>9}{'fill %':>9}{'net INR':>16}{'viol':>6}"]
    for e in lad["ladder"] + lad["extras"] + lad.get("ablation", []):
        k = e["kpis"]
        label = e["policy"] + ("+nv" if e.get("flags", {}).get("newsvendor") else "")
        lines.append(f"{label:<14}{k['spoilage_kg']:>11.2f}{k['spoilage_pct']:>9.2f}"
                     f"{k['demand_fulfillment_pct']:>9.2f}{k['net_inr']:>16,.2f}{k['violations']:>6}")
    lines.append(f"\nwaterfall ({wf['baseline']} -> {wf['plan']})")
    for s in wf["steps"]:
        fmt = ">16,.2f" if s["type"] == "total" else ">+16,.2f"
        lines.append(f"  {s['label']:<26}{s['value']:{fmt}}")
    return "\n".join(lines)
