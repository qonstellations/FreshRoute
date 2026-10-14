"""Seeded synthetic scenario generator, v3 (ARCHITECTURE.md section 5 and A-47..A-50;
DATABASE.md sections 3.1-3.10). SYNTHETIC: no organizer data and no Agmarknet snapshot, so
prices come from the static, report-grounded table in `constants`. Every scenario.json says so.

Structure (A-49): a Kolar/Chikkaballapur -> Bengaluru-region network with real node
coordinates. Lane times follow road distance, outlet type drives windows, prices, baskets
and receiving capacity, demand roughly matches supply and is only placed on days some lane
can actually deliver, and the fleet's trips per day follow its lane times.
"""
from __future__ import annotations

from .build import generate, generate_committed
from .constants import COMMITTED, GENERATOR_VERSION, HIDDEN_SEEDS, PRICE_SOURCE
from .geography import DESTS, HUBS, _km

__all__ = ["COMMITTED", "DESTS", "GENERATOR_VERSION", "HIDDEN_SEEDS", "HUBS", "PRICE_SOURCE",
           "_km", "generate", "generate_committed"]
