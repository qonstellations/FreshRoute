"""Template narration: the ARCHITECTURE 14.4 guard as a test."""
import json
import re
from pathlib import Path

import pytest

from freshroute.engine.narrator import template_narration

FIX = Path(__file__).parent / "fixtures"
DIFF = json.loads((FIX / "diff_example.json").read_text(encoding="utf-8"))
METRICS = json.loads((FIX / "metrics_example.json").read_text(encoding="utf-8"))
NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")


def _numbers(obj) -> list[float]:
    """Every number in a JSON value, including digits inside strings (ids like B014)."""
    if isinstance(obj, dict):
        return [x for v in obj.values() for x in _numbers(v)]
    if isinstance(obj, list):
        return [x for v in obj for x in _numbers(v)]
    if isinstance(obj, bool) or obj is None:
        return []
    if isinstance(obj, (int, float)):
        return [abs(float(obj))]
    return [float(s.replace(",", "")) for s in NUM.findall(str(obj))]


def _guard(text: str, *sources, extra=()) -> None:
    pool = [x for s in sources for x in _numbers(s)] + list(extra)
    for tok in NUM.findall(text):
        dec = len(tok.split(".")[1]) if "." in tok else 0
        x = float(tok.replace(",", ""))
        assert any(abs(round(v, dec) - x) < 10 ** -dec / 2 + 1e-9 for v in pool), tok


def test_every_number_comes_from_the_json():
    text = template_narration(DIFF, METRICS)
    assert "+1 more" in text and "Re-planned in 3.4 s" in text
    _guard(text, DIFF, METRICS, extra=[len(DIFF["moved_batches"]), 1, 3])


def test_empty_diff_and_determinism():
    diff = {"event_id": "E-002", "at_h": 0.0}
    text = template_narration(diff, METRICS)
    assert "kept every batch" in text and text == template_narration(diff, METRICS)
    _guard(text, diff, METRICS, extra=[0])


def test_guard_catches_invented_numbers():
    with pytest.raises(AssertionError):
        _guard("net 999,999 INR", DIFF, METRICS)
