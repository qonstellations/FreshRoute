"""costmodel.py formulas (ARCHITECTURE.md section 7)."""
import pytest

from freshroute.config import FLOAT_TOL
from freshroute.domain import costmodel as cm


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
    assert cm.cost_of_goods_sold(20, 15) == pytest.approx(300, abs=FLOAT_TOL)
    assert cm.net(1000, 300, 300, 200, 80) == pytest.approx(120, abs=FLOAT_TOL)


def test_margin_uplift_salvage_cap():
    # (40 - 15) * 0.9 - 2 - 1 = 19.5
    assert cm.shipped_margin(40, 0.1, 15, 2, 1) == pytest.approx(19.5, abs=FLOAT_TOL)
    assert cm.demand_uplift(1.0, 0.2) == pytest.approx(1.2, abs=FLOAT_TOL)
    assert cm.demand_uplift(5.0, 0.5) == pytest.approx(1.5, abs=FLOAT_TOL)  # MAX_UPLIFT cap
    assert cm.salvage_cap_frac(20, 5) == pytest.approx(0.75, abs=FLOAT_TOL)
    assert cm.salvage_cap_frac(0, 5) == 0.0
