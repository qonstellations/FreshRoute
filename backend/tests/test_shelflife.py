"""ARCHITECTURE.md section 7.1 worked example plus decay properties."""
import pytest

from freshroute.config import FLOAT_TOL, Q10_DEFAULT
from freshroute.domain.shelflife import decay, usable_life_at_arrival

MIN_SELL_WINDOW_H = 24  # section 7.1 example value, test-local
# (transit_temp_c, travel_h, usable_h, feasible); RSL 100, wait 5, handling 2, store/ref 20 C, q10 2
CASES = [(10, 12, 87, True), (30, 12, 69, True), (30, 40, 13, False)]


@pytest.mark.parametrize("t,travel,expected,feasible", CASES)
def test_worked_example(t, travel, expected, feasible):
    got = usable_life_at_arrival(100, 5, travel, 2, 20, t, 20, 2)
    assert got == pytest.approx(expected, abs=FLOAT_TOL)
    assert (got >= MIN_SELL_WINDOW_H) is feasible


def test_decay_at_ref_is_one():
    assert decay(20, 20, 2) == pytest.approx(1.0, abs=FLOAT_TOL)
    assert decay(7.5, 7.5, Q10_DEFAULT) == pytest.approx(1.0, abs=FLOAT_TOL)


def test_decay_known_values():
    assert decay(10, 20, 2) == pytest.approx(0.5, abs=FLOAT_TOL)
    assert decay(30, 20, 2) == pytest.approx(2.0, abs=FLOAT_TOL)


def test_decay_monotonic_in_temperature():
    vals = [decay(t, 20, 2) for t in range(-5, 41, 5)]
    assert all(a < b for a, b in zip(vals, vals[1:], strict=False))


def test_zero_travel():
    got = usable_life_at_arrival(100, 5, 0, 2, 20, 30, 20, 2)
    assert got == pytest.approx(93, abs=FLOAT_TOL)


def test_negative_result_not_clamped():
    got = usable_life_at_arrival(10, 0, 40, 2, 20, 30, 20, 2)
    assert got == pytest.approx(10 - 80 - 2, abs=FLOAT_TOL)
    assert got < 0
