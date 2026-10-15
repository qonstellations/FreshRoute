"""Attribution ladder and waterfall (ARCHITECTURE.md section 12): runs every ladder policy
through runs.runner.run (one simulator); writes ladder.json + waterfall.json (DATABASE.md 5.11)."""
from __future__ import annotations

import json
from pathlib import Path

from freshroute.config import BASELINE, PLAN
from freshroute.data.io import load_scenario
from freshroute.runs import naming
from freshroute.runs.runner import run

LADDER = ("fifo", "fefo", "milp")
EXTRAS = ("last_day_50",)
TOLERANCE_INR = 0.01
ABLATION_DELTAS = ("net_inr", "spoilage_kg", "spoilage_pct", "demand_fulfillment_pct")


def waterfall(base: dict, plan: dict) -> list[dict]:
    """Steps from two economics_inr dicts (ARCH section 12); deltas sum to net_P - net_B."""
    def d(k: str) -> float:
        return float(plan.get(k, 0.0)) - float(base.get(k, 0.0))
    return [
        {"label": "Baseline net", "value": float(base.get("net", 0.0)), "type": "total"},
        {"label": "Spoilage cost avoided", "value": 0.0 - d("spoilage_cost"), "type": "delta"},
        {"label": "Extra sales (list price)", "value": d("gross_revenue_at_list"), "type": "delta"},
        {"label": "Cost of extra goods sold", "value": 0.0 - d("cost_of_goods_sold"),
         "type": "delta"},
        {"label": "Extra transport", "value": 0.0 - d("transport"), "type": "delta"},
        {"label": "Extra handling", "value": 0.0 - d("handling"), "type": "delta"},
        {"label": "Discounts given", "value": 0.0 - d("discount_cost"), "type": "delta"},
        {"label": "FreshRoute net", "value": float(plan.get("net", 0.0)), "type": "total"},
    ]


def run_ladder(scenario: str, seed: int, out: str | None = None,
               newsvendor: bool = False) -> Path:
    """Run ladder + extras policies; write <out or outputs>/<name>__ladder__s<seed>/; return it.
    `newsvendor` adds an `ablation` entry: PLAN re-run with --newsvendor (section 14.3)."""
    root = Path(out) if out else Path("outputs")
    name = load_scenario(scenario).name
    for pol in LADDER + EXTRAS:
        run(scenario, pol, seed, str(root / naming.run_id(name, pol, seed)))
    ablation = None
    if newsvendor:  # flag off: ladder.json unchanged (AGENTS.md rule 9)
        nv_id = naming.run_id(name, PLAN, seed, True)
        run(scenario, PLAN, seed, str(root / nv_id), newsvendor=True)
        ablation = nv_id
    return write_ladder(root, name, seed, ablation)


def _metrics(d: Path) -> dict:
    return json.loads((d / "metrics.json").read_text(encoding="utf-8"))


def write_ladder(root: Path, name: str, seed: int, ablation: str | None = None) -> Path:
    """(Re)write ladder.json + waterfall.json from the run directories now under `root`, so the
    ladder always shows the latest run of each policy (A-55). `ablation` = newsvendor run id."""
    metrics = {p: _metrics(root / naming.run_id(name, p, seed)) for p in LADDER + EXTRAS}
    out_dir = root / naming.run_id(name, "ladder", seed)
    out_dir.mkdir(parents=True, exist_ok=True)
    ladder = {
        "scenario": name, "seed": seed, "realization": "base",
        "official_baseline": None,  # no organizer baseline procedure published yet
        "ladder": [{"policy": p, "kpis": metrics[p]["kpis"]} for p in LADDER],
        "extras": [{"policy": p, "kpis": metrics[p]["kpis"]} for p in EXTRAS],
    }
    if ablation and (root / ablation / "metrics.json").is_file():
        k, ref = _metrics(root / ablation)["kpis"], metrics[PLAN]["kpis"]
        ladder["ablation"] = [{
            "policy": PLAN, "flags": {"newsvendor": True}, "run_id": ablation, "vs": PLAN,
            "kpis": k, "delta": {key: k[key] - ref[key] for key in ABLATION_DELTAS}}]
    wf = {"baseline": BASELINE, "plan": PLAN, "tolerance_inr": TOLERANCE_INR,
          "steps": waterfall(metrics[BASELINE]["economics_inr"], metrics[PLAN]["economics_inr"])}
    (out_dir / "ladder.json").write_text(json.dumps(ladder, indent=2) + "\n", encoding="utf-8")
    (out_dir / "waterfall.json").write_text(json.dumps(wf, indent=2) + "\n", encoding="utf-8")
    return out_dir


def refresh_ladder(out_dir: Path, name: str, policy: str, seed: int) -> None:
    """After a plain run of a ladder policy into `<root>/<run_id>`: if a ladder for the same
    scenario and seed exists under `root` and every ladder run is on disk, rewrite it."""
    if policy not in LADDER + EXTRAS or out_dir.name != naming.run_id(name, policy, seed):
        return
    root = out_dir.parent
    lad = root / naming.run_id(name, "ladder", seed) / "ladder.json"
    if not lad.is_file():
        return
    runs_dirs = [root / naming.run_id(name, p, seed) for p in LADDER + EXTRAS]
    if not all((d / "metrics.json").is_file() for d in runs_dirs):
        return
    try:
        versions = {_metrics(d).get("schema_version") for d in runs_dirs}
        if len(versions) != 1:
            return  # skip refresh if on-disk ladder runs have mismatched schema versions
        old = json.loads(lad.read_text(encoding="utf-8")).get("ablation") or [{}]
        write_ladder(root, name, seed, old[0].get("run_id"))
    except Exception:
        # A ladder refresh issue must never fail the underlying run (Non-negotiable 6)
        pass


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
