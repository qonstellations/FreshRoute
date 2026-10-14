"""Template narration (ARCHITECTURE.md section 14.4): plain sentences over diff.json
(DATABASE.md 5.13) and metrics.json (5.7). No network, no LLM, no arithmetic: every number
printed is read from the given JSON (only the "+N more" count is a len()).
"""
from __future__ import annotations

_SHOW_MOVES = 3


def _moved(m: dict) -> str:
    f, t = m["from"], m["to"]
    return (f"{m['batch_id']} moved {f['dest_id']} day {f['dispatch_day']} -> "
            f"{t['dest_id']} day {t['dispatch_day']} ({m['kg']:,.0f} kg)")


def template_narration(diff: dict, metrics: dict) -> str:
    """Narrate one replan diff plus the run's metrics as a short paragraph."""
    moved = diff.get("moved_batches") or []
    changes = diff.get("discount_changes") or []
    out = [f"Event {diff['event_id']} at hour {diff['at_h']:g}: "
           f"{diff.get('frozen_shipments', 0)} shipments already dispatched stay frozen."]
    if moved:
        lines = "; ".join(_moved(m) for m in moved[:_SHOW_MOVES])
        more = f"; +{len(moved) - _SHOW_MOVES} more" if len(moved) > _SHOW_MOVES else ""
        out.append(f"Replan moved {len(moved)} batches: {lines}{more}.")
    else:
        out.append("Replan kept every batch on its destination.")
    if changes:
        c = changes[0]
        out.append(f"Markdowns changed: {len(changes)}, e.g. lot {c['lot_id']} day {c['day']} "
                   f"{c['from_pct']}% -> {c['to_pct']}%.")
    d = diff.get("delta_kpis") or {}
    if d:
        out.append(f"Versus keeping the old plan: net {d['net_inr']:+,.0f} INR, "
                   f"spoilage {d['spoilage_kg']:+,.0f} kg, "
                   f"fulfillment {d['demand_fulfillment_pct']:+.1f} pp.")
    if "solve_seconds" in diff:
        out.append(f"Replanned in {diff['solve_seconds']:.1f} s.")
    k = metrics["kpis"]
    out.append(f"Run {metrics['run_id']}: net {k['net_inr']:,.0f} INR, "
               f"spoilage {k['spoilage_kg']:,.0f} kg.")
    return " ".join(out)
