"""Regenerate every committed scenario under data/scenarios."""
from pathlib import Path

from . import COMMITTED, generate_committed

_root = Path(__file__).resolve().parents[4] / "data" / "scenarios"
for _name in COMMITTED:
    generate_committed(_name, _root)
