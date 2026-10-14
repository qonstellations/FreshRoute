"""costmodel.py formulas (ARCHITECTURE.md section 7)."""
import pytest

from freshroute import costmodel as cm
from freshroute.config import FLOAT_TOL


def test_revenue_identity():
    g = cm.gross_revenue_at_list(100, 50)
    d = cm.discount_cost(100, 50, 0.2)
    r = cm.revenue(100, 50, 0.2)
    assert g == pytest.approx(5000, abs=FLOAT_TOL)
    assert d == pytest.approx(1000, abs=FLOAT_TOL)
    assert r == pytest.approx(g - d, abs=FLOAT_TOL)


def test_spoilage_transport_handling_net():
    assert cm.spoilage(10, 10, 1, 3) == pytest.approx(80, abs=FLOAT_TOL)
    assert cm.transport(2, 500, 100, 3) == pytest.approx(1300, abs=FLOAT_TOL)
    assert cm.handling(100, 2) == pytest.approx(200, abs=FLOAT_TOL)
    assert cm.net(1000, 300, 200, 80) == pytest.approx(420, abs=FLOAT_TOL)
