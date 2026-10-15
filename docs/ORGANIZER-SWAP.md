# If the organizers publish their material

These two tables used to live in the README. They are the checklist for the day an official cost model or data format appears: theirs overrides ours (Rule 1). Nothing has been published so far, so every row is still on our own schema.

## Organizer mapping

To confirm when organizer data is published. Template from `docs/DATABASE.md` §8. Until then every row is on our own schema (synthetic data is allowed). If the organizers publish a format or cost model, theirs overrides ours. The organizer baseline policy (`organizer_baseline`) is intentionally not implemented until their procedure is published.

| Our table.column | Organizer file.column | Transform | Status |
|---|---|---|---|
| `batches.*` (qty, RSL, temp, availability, origin) | our own field | none | own schema; confirm against organizer data |
| `commodities.base_shelf_life_h / ref_temp_c / q10` | our own field | none | own schema; confirm against organizer data |
| `commodities.min_sell_window_h` | our own field | none | own schema; confirm against organizer data |
| `commodities.handling_loss_pct` | our own field | none | own schema; confirm against organizer data |
| `commodities.unit_cost / disposal_cost / salvage_value` | our own field | none | own schema; confirm against organizer data |
| `commodities.price_elasticity / max_discount_pct` | our own field | none | own schema; confirm against organizer data |
| `destinations.receive_cap_kg_day` | our own field | none | own schema; confirm against organizer data |
| `destinations.handling_time_h / handling_cost_inr_kg` | our own field | none | own schema; confirm against organizer data |
| `destinations.window_open_h / window_close_h` (+ `window_mode`) | our own field | none; absolute hours from day 0 at 00:00 (A-01) | own schema; confirm against organizer data |
| `demand.demand_kg_p10/p50/p90` | our own field | none | own schema; confirm against organizer data |
| `prices.*` | our own field | none | own schema; confirm against organizer data |
| `lanes.travel_h_p50/p90` | our own field | none | own schema; confirm against organizer data |
| `lanes.cost_fixed_inr_trip / cost_var_inr_kg` | our own field | none | own schema; confirm against organizer data |
| `lanes.transit_temp_c` | our own field | none | own schema; confirm against organizer data |
| `lanes.departure_slots` (rail) | our own field | none | own schema; confirm against organizer data |
| `vehicles.*` (capacity, trips/day, availability) | our own field | none | own schema; confirm against organizer data |
| `events.*` | our own field (`docs/DATABASE.md` §6) | none | own schema; confirm against organizer data |
| Origin handling cost | our own field: 0 (A-07) | none | own schema; confirm against organizer data |
| Discount / markdown rules (caps, elasticity) | only the `last_day_50` baseline discounts (`docs/ARCHITECTURE.md` §10, §12) | none | own schema; confirm against organizer data |
| Spoilage definition and cost | our own definition (`docs/ARCHITECTURE.md` §7) | none | own schema; confirm against organizer data |
| Fulfillment definition | our own definition (`docs/ARCHITECTURE.md` §7) | none | own schema; confirm against organizer data |
| Hard-constraint list (what counts as a violation) | codes in `validator/` as built | none | own schema; confirm against organizer data |
| Submission/plan output format (for `organizer_baseline` export) | our own `plan.csv` (`docs/DATABASE.md` §5.2) | none | own schema; confirm against organizer data |

## Cost-model comparison

Every coefficient or formula in `docs/ARCHITECTURE.md` §7 that must change if the organizers' model differs. Parameter values live in `config.py` (`docs/ARCHITECTURE.md` §19); formulas live in `domain/costmodel.py`. No organizer cost model has been published; every row is a confirm-when-published item.

| Item (ARCHITECTURE §7) | Where | Status |
|---|---|---|
| Decay law `decay(T) = q10 ^ ((T - ref_temp_c) / 10)` and `Q10_DEFAULT` (2.0, unverified convention) | `domain/costmodel.py` / `config.py` | confirm when published |
| Usable life at arrival: `RSL - wait_h*decay(T_store) - travel_h*decay(T_transit) - handling_h` | `domain/costmodel.py` | confirm when published |
| Feasibility rule `usable life >= min_sell_window_h` and arrival inside delivery window | `domain/costmodel.py` | confirm when published |
| Planning travel time `travel_h_p50` | `domain/costmodel.py` | confirm when published |
| Dispatch hour `DISPATCH_HOUR` (5) | `config.py` | confirm when published |
| Effective demand `demand * (1 + min(eps*discount, MAX_UPLIFT))` and `MAX_UPLIFT` (0.5) | `domain/costmodel.py` / `config.py` | confirm when published |
| Sold `min(on_hand_sellable, effective_demand)`, FEFO within destination | `domain/costmodel.py` | confirm when published |
| Spoiled kg: `handling_loss_frac * delivered` + unsold at expiry + undispatched expiring at origin | `domain/costmodel.py` | confirm when published |
| Revenue `sum sold * price * (1 - discount)` | `domain/costmodel.py` | confirm when published |
| Transport `trips * cost_fixed_inr_trip + kg * cost_var_inr_kg` | `domain/costmodel.py` | confirm when published |
| Handling `kg_delivered * handling_cost_inr_kg`; origin handling = 0 (A-07) | `domain/costmodel.py` | confirm when published |
| Spoilage cost `spoiled_kg * (unit_cost + disposal_cost - salvage_value)` | `domain/costmodel.py` | confirm when published |
| Discount cost reported separately, never subtracted twice | `domain/costmodel.py` | confirm when published |
| Net `Revenue - Transport - Handling - Spoilage cost` | `domain/costmodel.py` | confirm when published |
| Demand fulfillment `sum min(sold, base_demand) / sum base_demand`; minimum destination fill rate | `domain/costmodel.py` | confirm when published |
| Spoilage % `spoiled_kg / sum batches.qty_kg * 100` | `domain/costmodel.py` | confirm when published |
| Feasibility score = hard violations from `validator/` | `validator/` (independent re-implementation) | confirm when published |
| Carry-over at horizon end (valued 0, A-06) | `domain/costmodel.py` | confirm when published |
| `last_day_50` baseline: `DISCOUNT_TIME_TRIGGER_H` (24), `LAST_DAY_DISCOUNT_PCT` (50) | `config.py` | confirm when published |
