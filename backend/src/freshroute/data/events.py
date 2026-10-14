"""Replan events (ARCHITECTURE.md section 14.2; schema DATABASE.md section 6, semantics A-14).

`Event` validates syntax (type, target shape, magnitude range); `check_targets` validates the
ids against a scenario; `apply_event` returns a changed copy of the scenario. Nothing here
plans or scores; an LLM parser, if one is ever added, may only produce an `Event`.
"""
from __future__ import annotations

import json
import math
from dataclasses import replace
from pathlib import Path
from typing import Literal

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, model_validator

from freshroute.config import HOURS_PER_DAY
from freshroute.data.io import Scenario

EventType = Literal["route_delay", "capacity_drop", "demand_spike", "new_order", "price_shock"]
_WILD_COM = ("demand_spike", "price_shock")  # `*` allowed for the commodity


class EventError(ValueError):
    """Event is syntactically valid but does not fit the scenario."""


class Event(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: str = Field(min_length=1)
    type: EventType
    target: str = Field(min_length=1)
    magnitude: float
    at_h: float = Field(ge=0)
    note: str | None = None  # never used by the solver

    @model_validator(mode="after")
    def _check(self) -> Event:
        m, t = self.magnitude, self.target
        if not math.isfinite(m) or not math.isfinite(self.at_h):
            raise ValueError("magnitude and at_h must be finite")
        if self.type == "route_delay":
            parts = t.split("|")
            if len(parts) != 3 or not all(parts):
                raise ValueError("route_delay target must be origin|dest_id|mode")
            if m < 0:
                raise ValueError("route_delay magnitude (hours) must be >= 0")
        elif self.type == "capacity_drop":
            kind, _, ident = t.partition(":")
            if kind not in ("vehicle", "dest") or not ident:
                raise ValueError("capacity_drop target must be vehicle:<id> or dest:<id>")
            if not 0 <= m <= 1:
                raise ValueError("capacity_drop magnitude is a fraction lost, 0-1")
        else:
            kind, _, rest = t.partition(":")
            dest, _, com = rest.partition("|")
            if kind != "dest" or not dest or not com or "|" in com or dest == "*":
                raise ValueError(f"{self.type} target must be dest:<dest_id>|<commodity>")
            if com == "*" and self.type not in _WILD_COM:
                raise ValueError(f"{self.type} target does not allow '*' for the commodity")
            if self.type == "new_order" and m < 0:
                raise ValueError("new_order magnitude (kg) must be >= 0")
            if self.type in _WILD_COM and m <= 0:
                raise ValueError(f"{self.type} magnitude (multiplier) must be > 0")
        return self

    @property
    def day(self) -> int:
        return int(self.at_h // HOURS_PER_DAY)


def load_event(path: str | Path) -> Event:
    """Read and validate one event JSON file (DATABASE.md section 6)."""
    return Event.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))


def lane_mask(lanes, target: str):
    m = None
    for col, want in zip(("origin", "dest_id", "mode"), target.split("|"), strict=True):
        hit = lanes[col] == want if want != "*" else lanes[col].notna()
        m = hit if m is None else m & hit
    return m


def _dest_com_mask(df, ev: Event):
    dest, _, com = ev.target.partition(":")[2].partition("|")
    m = df["dest_id"] == dest
    return m if com == "*" else m & (df["commodity"] == com)


def check_targets(sc: Scenario, ev: Event) -> None:
    """Raise EventError if the event's target names ids the scenario does not have."""
    t = sc.tables
    if ev.type == "route_delay":
        if not lane_mask(t["lanes"], ev.target).any():
            raise EventError(f"{ev.event_id}: no lane matches {ev.target!r}")
        return
    kind, _, rest = ev.target.partition(":")
    if ev.type == "capacity_drop":
        tab, col = ("vehicles", "vehicle_id") if kind == "vehicle" else ("destinations", "dest_id")
        if rest not in set(t[tab][col]):
            raise EventError(f"{ev.event_id}: unknown {col} {rest!r}")
        return
    dest, _, com = rest.partition("|")
    if dest not in set(t["destinations"]["dest_id"]):
        raise EventError(f"{ev.event_id}: unknown dest_id {dest!r}")
    if com != "*" and com not in set(t["commodities"]["commodity"]):
        raise EventError(f"{ev.event_id}: unknown commodity {com!r}")


def apply_event(sc: Scenario, ev: Event) -> Scenario:
    """Changed world: a copy of `sc` with the event's effect (DATABASE.md section 6 table).
    Time-dependent effects (capacity "from at_h") are applied to the whole table; replan.py
    keeps frozen shipments out of their reach."""
    check_targets(sc, ev)
    t = {k: v.copy() for k, v in sc.tables.items()}
    m = ev.magnitude
    if ev.type == "route_delay":
        hit = lane_mask(t["lanes"], ev.target)
        t["lanes"].loc[hit, ["travel_h_p50", "travel_h_p90"]] += m
    elif ev.type == "capacity_drop":
        kind, _, ident = ev.target.partition(":")
        tab, key, col = (("vehicles", "vehicle_id", "capacity_kg") if kind == "vehicle"
                         else ("destinations", "dest_id", "receive_cap_kg_day"))
        t[tab][col] = t[tab][col].astype(float)
        t[tab].loc[t[tab][key] == ident, col] *= 1 - m
    elif ev.type == "price_shock":
        p = t["prices"]
        hit = _dest_com_mask(p, ev) & (p["day"] >= ev.day)
        cols = ["price_inr_kg", "price_min", "price_max"]
        p[cols] = p[cols].astype(float)
        p.loc[hit, cols] *= m
    else:  # demand_spike / new_order
        d = t["demand"]
        cols = ["demand_kg_p10", "demand_kg_p50", "demand_kg_p90"]
        d[cols] = d[cols].astype(float)
        if ev.type == "demand_spike":
            d.loc[_dest_com_mask(d, ev) & (d["day"] >= ev.day), cols] *= m
        else:
            dest, _, com = ev.target.partition(":")[2].partition("|")
            hit = _dest_com_mask(d, ev) & (d["day"] == ev.day)
            if hit.any():
                d.loc[hit, cols] += m
            else:  # no demand row for that day yet: the order is the demand
                row = {"dest_id": dest, "commodity": com, "day": ev.day, "event_flag": ev.event_id,
                       **dict.fromkeys(cols, m)}
                t["demand"] = pd.concat([d, pd.DataFrame([row])], ignore_index=True)
    return replace(sc, tables=t)

