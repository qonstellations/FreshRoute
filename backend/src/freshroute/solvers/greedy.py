"""FEFO-greedy allocation and its lookups (ARCHITECTURE.md sections 9.5 and 12)."""
from __future__ import annotations

import pandas as pd

from freshroute.config import FLOAT_TOL, OVERSHIP_SLACK
from freshroute.io import Scenario


def lookups(sc: Scenario, override: dict | None = None):
    t = sc.tables
    veh = t["vehicles"].set_index("vehicle_id")
    lanes = t["lanes"].set_index(["origin", "dest_id", "mode"])
    dest = t["destinations"].set_index("dest_id")
    target = t["demand"].set_index(["dest_id", "commodity", "day"]).demand_kg_p50.to_dict()
    target.update(override or {})  # demand_cap_override (section 14.3): {(d, c, day): kg}
    return veh, lanes, dest, target


def classes(veh: pd.DataFrame, fleet: pd.DataFrame | None):
    """Trip classes per arc vehicle: (class table, {arc vehicle_id: [class ids]}). Identity
    (every vehicle its own class) unless the section 9.5 fallback pools the fleet."""
    f = veh.assign(lane_class=veh.index) if fleet is None else fleet
    return f, {v: list(g.index) for v, g in f.groupby("lane_class", sort=True)}


def fefo_greedy(sc: Scenario, arcs, batches, override: dict | None = None,
            overship: float = OVERSHIP_SLACK, used: dict | None = None,
            fleet: pd.DataFrame | None = None):
    """FEFO-greedy over feasible arcs honouring C2-C5 (earliest-expiry batch first)."""
    veh, _, dest, target = lookups(sc, override)
    f, cls = classes(veh, fleet)
    tgt = {k: v * (1 + overship) for k, v in target.items()}
    recv: dict = dict((used or {}).get("recv", {}))  # (d, day) keys only; frozen arrivals
    load: dict = {}  # (v,d,day) -> kg left on already-opened trips
    trips_day: dict = dict((used or {}).get("trips", {}))
    n: dict = {}
    x = [0.0] * len(arcs)
    expiry = batches.available_from_h + batches.remaining_shelf_life_h
    for bid in sorted(batches.index, key=lambda b: (expiry[b], b)):
        left = float(batches.qty_kg[bid])
        sub = arcs[arcs.batch_id == bid].sort_values(
            ["coef", "dest_id", "vehicle_id", "dispatch_day"], ascending=[False, True, True, True])
        for i, a in sub.iterrows():
            kd, ka = (a.dest_id, a.commodity, a.arrival_day), (a.dest_id, a.arrival_day)
            k = (a.vehicle_id, a.dest_id, a.dispatch_day)
            while left > FLOAT_TOL:
                room = min(tgt.get(kd, 0.0) - recv.get(kd, 0.0),
                           float(dest.receive_cap_kg_day[a.dest_id]) - recv.get(ka, 0.0))
                if room <= FLOAT_TOL:
                    break
                if load.get(k, 0.0) <= FLOAT_TOL:  # open a trip on the first class with a slot
                    c = next((c for c in cls[a.vehicle_id] if trips_day.get((c, a.dispatch_day), 0)
                              < int(f.max_trips_day[c])), None)
                    if c is None:
                        break
                    trips_day[(c, a.dispatch_day)] = trips_day.get((c, a.dispatch_day), 0) + 1
                    n[(c, *k[1:])] = n.get((c, *k[1:]), 0) + 1
                    load[k] = load.get(k, 0.0) + float(f.capacity_kg[c])
                q = min(left, room, load[k])
                x[i] += q
                recv[kd] = recv.get(kd, 0.0) + q
                recv[ka] = recv.get(ka, 0.0) + q
                load[k] -= q
                left -= q
    return x, n
