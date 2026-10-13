"""Stub for the ARCHITECTURE.md section 7.1 worked example; F-01 removes the xfail."""
import pytest

from freshroute.shelflife import usable_life_at_arrival

# (transit_temp_c, travel_h, usable_h); RSL 100, wait 5, handling 2, store/ref 20 C, q10 2
CASES = [(10, 12, 87), (30, 12, 69), (30, 40, 13)]


@pytest.mark.xfail(raises=NotImplementedError, strict=True)
@pytest.mark.parametrize("t,travel,expected", CASES)
def test_worked_example(t, travel, expected):
    assert usable_life_at_arrival(100, 5, travel, 2, 20, t, 20, 2) == pytest.approx(expected)
