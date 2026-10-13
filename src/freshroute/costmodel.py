"""Cost formulas (ARCHITECTURE.md section 7, Economics). The only place money maths lives.

Pure functions on floats / pandas Series; coefficients arrive as arguments from scenario
tables (commodities, destinations, lanes, prices). Discounts are fractions (0-1).
"""
from __future__ import annotations


def gross_revenue_at_list(sold_kg, price_inr_kg):
    return sold_kg * price_inr_kg


def discount_cost(sold_kg, price_inr_kg, discount_frac):
    """Reported separately; already netted inside revenue, never subtracted again."""
    return sold_kg * price_inr_kg * discount_frac


def revenue(sold_kg, price_inr_kg, discount_frac):
    return sold_kg * price_inr_kg * (1.0 - discount_frac)


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


def net(revenue_inr, transport_inr, handling_inr, spoilage_inr):
    return revenue_inr - transport_inr - handling_inr - spoilage_inr
