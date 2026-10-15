"""Discount advisor (ARCHITECTURE.md sections 10 and 15; DATABASE.md section 5.15; A-54).

For every (dest, commodity, day) of the simulated ledger that ends the day with stock left,
tests each markdown on a grid up to the commodity's cap and the salvage floor, using the
same demand-uplift rule as the simulator, and reports the best one with its estimated INR
effect and the reason. Advice only: the reported net still comes from the simulator (rule 3).
"""
from __future__ import annotations

from freshroute.config import ADVICE_STEP_PCT, FLOAT_TOL
from freshroute.data.io import Scenario
from freshroute.domain import costmodel as cm


def _effect(r, c, frac: float) -> float:
    """Estimated INR change of a cut `frac` on one ledger row: price change on what sells
    anyway, plus the extra kg the uplift sells out of what would otherwise expire (saves
    disposal minus salvage on top of the revenue) or be carried over (costs COGS)."""
    left_exp, left_carry = r.unsold_expired_kg, r.on_hand_end_kg
    extra = min(r.base_demand_kg * (cm.demand_uplift(c.price_elasticity, frac) - 1.0),
                left_exp + left_carry)
    from_exp = min(extra, left_exp)
    from_carry = extra - from_exp
    p = r.price_inr_kg
    return (cm.revenue(r.sold_kg + extra, p, frac) - cm.revenue(r.sold_kg, p, r.discount_frac)
            + from_exp * (c.disposal_cost_inr_kg - c.salvage_value_inr_kg)
            - cm.cost_of_goods_sold(from_carry, c.unit_cost_inr_kg))


def advise(scenario: Scenario, sim: dict) -> list[dict]:
    led = sim["ledger"]
    if led.empty:
        return []
    com = scenario.tables["commodities"].set_index("commodity")
    out = []
    rows = led[(led.unsold_expired_kg + led.on_hand_end_kg > FLOAT_TOL)
               & (led.price_inr_kg > 0)].sort_values(["dest_id", "commodity", "day"])
    for r in rows.itertuples():
        c = com.loc[r.commodity]
        cap = min(c.max_discount_frac, cm.salvage_cap_frac(r.price_inr_kg, c.salvage_value_inr_kg))
        grid = [k * ADVICE_STEP_PCT / 100 for k in range(1, int(100 * cap // ADVICE_STEP_PCT) + 1)]
        best, gain = 0.0, 0.0
        for f in grid:
            g = _effect(r, c, f)
            if g > gain + FLOAT_TOL:
                best, gain = f, g
        step = ADVICE_STEP_PCT / 100
        be = 1.0 / (1.0 - step)  # pure-revenue break-even of the smallest cut: (1-L)(1+eL) > 1
        left = r.unsold_expired_kg + r.on_hand_end_kg
        if best > 0:
            why = (f"{100 * best:.0f}% off sells more of the {left:.0f} kg left; "
                   f"estimated +INR {gain:,.0f}")
        elif c.price_elasticity <= be:
            why = (f"elasticity {c.price_elasticity:g} is below the break-even {be:.2f}: "
                   f"a cut loses more on kg that sell anyway than it gains on the "
                   f"{left:.0f} kg left")
        else:
            why = f"no cut up to {100 * cap:.0f}% pays on the {left:.0f} kg left"
        out.append({"dest_id": r.dest_id, "commodity": r.commodity, "day": int(r.day),
                    "left_kg": float(left), "elasticity": float(c.price_elasticity),
                    "max_cut_pct": 100 * float(cap), "best_cut_pct": 100 * best,
                    "delta_net_inr": float(gain), "break_even_elasticity": be, "reason": why})
    return out
