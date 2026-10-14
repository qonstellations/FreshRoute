"""Run-id / output-directory naming (ARCHITECTURE.md section 17; DATABASE.md section 5)."""
from __future__ import annotations


def run_id(scenario: str, kind: str, seed: int, newsvendor: bool = False) -> str:
    """The one place output directories / job ids are named: <scenario>__<kind>__s<seed>[__nv].
    `kind` is a policy, "ladder", "stress" or "sensitivity"."""
    return f"{scenario}__{kind}__s{seed}{'__nv' if newsvendor else ''}"
