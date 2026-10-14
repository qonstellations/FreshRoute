"""Independent plan validator (ARCHITECTURE.md section 11; output DATABASE.md section 5.8).
Reads scenario tables + plan (+ discounts) and counts hard violations; never imports the
optimizer, feasibility, shelflife or costmodel modules (D-04)."""
from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from freshroute.io import Scenario
from validator.rules import demand_warnings, discount_rules, shipment_rules

SCHEMA_VERSION = 2


@dataclass
class ValidationReport:
    violations: list[dict] = field(default_factory=list)
    warnings: list[dict] = field(default_factory=list)

    @property
    def violation_total(self) -> int:
        return len(self.violations)

    @property
    def counts(self) -> dict[str, int]:
        return dict(sorted(Counter(x["code"] for x in self.violations).items()))

    def to_dict(self) -> dict:
        return {"schema_version": SCHEMA_VERSION, "violation_total": self.violation_total,
                "counts": self.counts, "violations": self.violations, "warnings": self.warnings}

    def write(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2) + "\n", encoding="utf-8")


def validate(
    scenario: Scenario, plan: pd.DataFrame, discounts: pd.DataFrame | None = None,
    overship_slack: float | None = None,
) -> ValidationReport:
    """Return hard violations (and demand-cap warnings if `overship_slack` is given)."""
    mode = scenario.meta.get("window_mode", "absolute")
    viol = shipment_rules(scenario.tables, plan, mode)
    if discounts is not None and len(discounts):
        viol += discount_rules(scenario.tables, discounts)
    warns = [] if overship_slack is None else demand_warnings(
        scenario.tables, plan, overship_slack)
    return ValidationReport(viol, warns)
