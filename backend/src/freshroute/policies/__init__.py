"""Policy registry (ARCHITECTURE.md section 12). Classes import lazily: pulp/HiGHS are slow."""
from __future__ import annotations

from importlib import import_module

REGISTRY = {  # name -> (module, class)
    "fifo": ("freshroute.policies.fifo", "FifoPolicy"),
    "fefo": ("freshroute.policies.fefo", "FefoPolicy"),
    "last_day_50": ("freshroute.policies.last_day_50", "LastDay50Policy"),
    "milp": ("freshroute.policies.milp", "MilpPolicy"),
    "milp_markdown": ("freshroute.policies.milp", "MilpMarkdownPolicy"),
}


def get_policy(name: str):
    """Instantiate a registered policy; KeyError for an unknown name."""
    mod, cls = REGISTRY[name]
    return getattr(import_module(mod), cls)()
