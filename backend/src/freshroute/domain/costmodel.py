"""Cost formulas (ARCHITECTURE.md section 7, Economics). The only place money maths lives.

Pure functions on floats / pandas Series; coefficients arrive as arguments from scenario
tables (commodities, destinations, lanes, prices). Discounts are fractions (0-1).

Accounting (A-48): stock is bought at unit_cost. Sold kg carry it as cost of goods sold;
spoiled kg carry it inside the spoilage cost; stock still alive at horizon end is inventory
held at cost (A-06), so it carries neither.
"""
from __future__ import annotations

from freshroute.config import MAX_UPLIFT


def gross_revenue_at_list(sold_kg, price_inr_kg):
    return sold_kg * price_inr_kg


def discount_cost(sold_kg, price_inr_kg, discount_frac):
    """Reported separately; already netted inside revenue, never subtracted again."""
    return sold_kg * price_inr_kg * discount_frac


def revenue(sold_kg, price_inr_kg, discount_frac):
    return sold_kg * price_inr_kg * (1.0 - discount_frac)


def demand_uplift(elasticity, discount_frac):
    """Demand multiplier under a markdown: 1 + min(eps * d, MAX_UPLIFT) (A-11)."""
    return 1.0 + min(elasticity * discount_frac, MAX_UPLIFT)


def salvage_cap_frac(price_inr_kg, salvage_value_inr_kg):
    """Largest discount that keeps the shelf price at or above salvage value."""
    return 1.0 - salvage_value_inr_kg / price_inr_kg if price_inr_kg > 0 else 0.0


def cost_of_goods_sold(sold_kg, unit_cost_inr_kg):
    return sold_kg * unit_cost_inr_kg


def transport(n_trips, fixed_inr_trip, kg, var_inr_kg):
    """Scalars or aligned Series: trips * fixed + kg * variable."""
    return n_trips * fixed_inr_trip + kg * var_inr_kg


def handling(delivered_kg, handling_cost_inr_kg):
    return delivered_kg * handling_cost_inr_kg


def spoilage_unit_cost(unit_cost_inr_kg, disposal_cost_inr_kg, salvage_value_inr_kg):
    return unit_cost_inr_kg + disposal_cost_inr_kg - salvage_value_inr_kg


def spoilage(spoiled_kg, unit_cost_inr_kg, disposal_cost_inr_kg, salvage_value_inr_kg):
    return spoiled_kg * spoilage_unit_cost(
        unit_cost_inr_kg, disposal_cost_inr_kg, salvage_value_inr_kg
    )


def shipped_margin(price_inr_kg, handling_loss_frac, unit_cost_inr_kg, var_inr_kg,
                   handling_cost_inr_kg):
    """INR per shipped kg if it all sells at list: (p - unit cost) on the kg that survive
    handling, minus variable transport and receiving handling. The handling-loss kg are
    priced separately, as spoilage."""
    return ((price_inr_kg - unit_cost_inr_kg) * (1 - handling_loss_frac)
            - var_inr_kg - handling_cost_inr_kg)


def net(revenue_inr, cogs_inr, transport_inr, handling_inr, spoilage_inr):
    return revenue_inr - cogs_inr - transport_inr - handling_inr - spoilage_inr
