"""Dispatch sheet: priority-ordered CSV and WhatsApp-style text (ARCHITECTURE.md section 15;
format in DATABASE.md 5.10). Written by `cli.run` for every run.
"""
from __future__ import annotations

import pandas as pd

from freshroute.config import HOURS_PER_DAY
from freshroute.io import Scenario

COLUMNS = (
    "vehicle_id", "trip_id", "dispatch_h", "depart_clock", "dest_id", "dest_name", "batch_id",
    "commodity", "kg", "priority_rank", "slack_h", "arrive_by_h", "note",
)


def _clock(h: float) -> str:
    """Absolute hour -> "HH:MM" of its day."""
    hh, mm = divmod(round(h * 60) % (HOURS_PER_DAY * 60), 60)
    return f"{hh:02d}:{mm:02d}"


def _n(x: float) -> str:
    """Readable number for a phone message: one decimal at most."""
    return f"{round(x, 1):g}"


def build(scenario: Scenario, plan: pd.DataFrame, trips: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    """Return (dispatch_sheet.csv frame, dispatch_sheet.txt text) for a plan."""
    dests = scenario.tables["destinations"]
    names = {}
    if "name" in dests.columns:
        names = {r.dest_id: r.name for r in dests.itertuples() if pd.notna(r.name) and r.name}
    commodity = dict(zip(scenario.tables["batches"].batch_id,
                         scenario.tables["batches"].commodity, strict=True))

    p = plan.sort_values(["priority_rank", "shipment_id"], kind="stable")
    df = pd.DataFrame({
        "vehicle_id": p.vehicle_id, "trip_id": p.trip_id, "dispatch_h": p.dispatch_h,
        "depart_clock": p.dispatch_h.map(_clock), "dest_id": p.dest_id,
        "dest_name": p.dest_id.map(lambda d: names.get(d, d)),
        "batch_id": p.batch_id, "commodity": p.batch_id.map(commodity), "kg": p.kg,
        "priority_rank": p.priority_rank, "slack_h": p.slack_h, "arrive_by_h": p.arrival_h,
        "note": "",
    }, columns=list(COLUMNS)).reset_index(drop=True)

    trip_day = dict(zip(trips.trip_id, trips.dispatch_day, strict=True))
    blocks = []
    for trip_id in dict.fromkeys(df.trip_id):  # trips in order of their most urgent load
        rows = df[df.trip_id == trip_id]
        first = rows.iloc[0]
        last = p.loc[p.trip_id == trip_id].sort_values("arrival_h").iloc[-1]
        load = " | ".join(f"{r.batch_id} {r.commodity} {_n(r.kg)} kg (slack {_n(r.slack_h)} h)"
                          for r in rows.itertuples())
        blocks.append(
            f"Vehicle {first.vehicle_id} | Trip {trip_id} | Depart {first.depart_clock} "
            f"(day {trip_day[trip_id]})\n"
            f"To: {first.dest_name}\n"
            f"Load: {load}\n"
            f"Arrive by: day {int(last.arrival_day)} {_clock(last.arrival_h)}"
        )
    return df, "\n\n".join(blocks) + ("\n" if blocks else "")
