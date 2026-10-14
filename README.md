# FreshRoute

Wild Bugs Hackathon 2026. FreshRoute is a hub-level decision tool for perishable produce. Given batches with remaining shelf life, destinations with demand and delivery windows, and vehicles with capacities, it decides **which batch goes where, when, and at what markdown**.

## What is built

- **Feasibility pre-filter** on shelf life, delivery windows and rail slots, then an **allocation MILP solved with HiGHS** (soft constraints, 30 s limit, FEFO-greedy fallback and warm start).
- **Disclosed tiered markdown rule** (`milp_markdown`) and baselines `fifo`, `fefo`, `last_day_50`.
- **One seeded simulator** scores every policy; policies never report their own net.
- **Independent validator** (`backend/src/validator/`) re-implements the maths and reports hard violations.
- **Attribution ladder and waterfall** (`freshroute ladder`), sensitivity, **Monte Carlo stress** with P10-P90 bands, **event-driven replan** with a diff, and a **newsvendor** demand target (flag).
- **FastAPI** service over the engine's own output files and a **React dashboard** that renders them. An LLM never decides; narration is template-based.
- **Generator v3**: real place names and coordinates (Kolar and Chikkaballapur hubs shipping to Bengaluru-area markets, Hosur/Tumakuru/Mysuru and long-haul Chennai and Hyderabad), lane times from road distance, demand about 0.9-1.1x supply. All quantities, demand, costs and prices are **synthetic**.

**Rule #1:** if the organizers publish a cost model or dataset format, theirs overrides everything in these docs.

## Documentation

| Doc | Purpose |
|---|---|
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | How the system works: cost model, MILP, markdown, simulator, add-ons, assumption log (§20) |
| [`docs/DATABASE.md`](docs/DATABASE.md) | Data contracts: input tables, output files, event schema, organizer mapping |
| [`DECISIONS.md`](DECISIONS.md) | Decision log |
| [`docs/RESEARCH-v1.md`](docs/RESEARCH-v1.md) | Historical background research (some figures secondhand; see its §H) |
| [`AGENTS.md`](AGENTS.md) | Setup, workflow and rules for contributors and AI assistants |

## Quickstart

Install (uv owns Python 3.13, pinned in `.python-version`; Node 22+ for the dashboard):

```bash
make setup             # uv sync + npm ci --prefix frontend
make check             # ruff + pytest + frontend build + validate the demo plan
make demo              # ladder + waterfall on the practice scenario, seed 42
make serve             # build the dashboard and serve it with the API on http://127.0.0.1:8000
```

Engine commands (all through `uv run`):

```bash
uv run freshroute generate                       # regenerate the committed synthetic scenarios
uv run freshroute run --scenario data/scenarios/practice --policy milp_markdown --seed 42
uv run freshroute ladder --scenario data/scenarios/practice --seed 42
uv run freshroute sensitivity --scenario data/scenarios/practice --seed 42
uv run freshroute stress --scenario data/scenarios/practice --seed 42
uv run freshroute replan --run <run dir> --event <event.json>
uv run freshroute demo
```

Run `uv run freshroute <command> --help` for flags. Other targets: `make test`, `make api`, `make web`, `make run-stub`.

## Results

All numbers below are **measured** on the **SYNTHETIC** `practice` scenario (3-day horizon, seed 42, base realization), copied from `outputs/demo_backup/practice__ladder__s42/` and `outputs/practice__stress__s42/`. They are not real-world data.

Net INR subtracts the cost of goods sold (procurement), so margins are realistic.

| Policy | Spoilage kg | Spoilage % | Fill % | Min dest fill % | Net INR | Violations |
|---|---|---|---|---|---|---|
| fifo | 937.0 | 1.73 | 77.6 | 34.7 | 318,668 | 19 |
| fefo | 904.1 | 1.67 | 64.5 | 0.0 | 271,027 | 0 |
| milp | 835.0 | 1.54 | 75.2 | 32.3 | 395,344 | 0 |
| milp_markdown | 835.0 | 1.54 | 75.2 | 32.3 | 395,344 | 0 |
| last_day_50 (extra) | 937.0 | 1.73 | 77.6 | 34.7 | 300,674 | 19 |

Reading it honestly:

- FIFO and `last_day_50` ignore shelf life and windows, so the validator flags 19 violations; their higher fill is not a feasible plan.
- Against FEFO (feasible, 0 violations), MILP adds about ₹124k net. Waterfall: spoilage cost avoided +₹1,858, extra sales +₹176,583, cost of the extra goods sold -₹122,539, transport +₹70,886 (lower transport cost), handling -₹2,472, discounts ₹0. The win comes mainly from **fulfilling more demand (64.5 % to 75.2 %) with fewer trips (higher utilisation)**. Spoilage falls only slightly (904 to 835 kg, 1.67 % to 1.54 %); it is not the main driver.
- `milp_markdown` equals `milp` on `practice` because the planner ships at most the p50 demand, so no lot carries surplus for markdown to sell. Markdown matters when demand falls short, which the stress test samples.

Monte Carlo stress (`milp_markdown` vs `fefo`, 200 sampled futures, base seed 42):

| Metric | Plan P10 / P50 / P90 | FEFO P10 / P50 / P90 |
|---|---|---|
| Net INR | 361,681 / 375,373 / 382,259 | 238,588 / 249,720 / 258,322 |
| Spoilage kg | 832.8 / 864.9 / 920.6 | 896.7 / 931.5 / 985.1 |
| Fill % | 71.1 / 72.3 / 73.3 | 60.7 / 61.8 / 62.9 |

The plan beats the baseline on net in 100 % of the 200 futures and on spoilage kg in 93.5 %.

No replan figure is reported here; `freshroute replan` runs on these runs but its output has not been reviewed enough to quote.

## Assumptions

The full assumption log is `docs/ARCHITECTURE.md` §20. Decisions are in `DECISIONS.md`.

## Sources

Real-world statistics are framing context, never model inputs. Each claim is labelled **verified** (checked against a primary source), **company-reported** (vendor statement, unaudited) or **unverified**. Last re-checked 2026-10-14.

| Figure we may say | Value | Source | Status |
|---|---|---|---|
| Post-harvest loss study | NABCONS for MoFPI, reference year 2020-22, **54 commodities**, **15 agro-climatic zones**, **292 districts** | [PIB PRID 2148529, 25 Jul 2025](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2148529) · [PIB PRID 2151371, 1 Aug 2025](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2151371) | **verified (primary)** |
| Tomato loss | **8.37 % farm stage + 3.25 % market stage = 11.62 %** of output | PIB PRID 2151371, Annexure-II | **verified (primary)** |
| Onion loss | **5.31 % + 1.96 % = 7.27 %** | PIB PRID 2151371, Annexure-II | **verified (primary)** |
| Loss ranges | Fruits **6.02-15.05 %**, vegetables **4.87-11.61 %** | MoFPI annexure to Lok Sabha USQ 2998, 6 Aug 2026 | **verified (primary)** |
| Tomato loss value | Post-harvest loss valued at about **₹5,921 crore** (NABCONS, 2020-22). The release gives no stage split and does not say it is annual: never say "a year" or "at market stage" | [PIB PRID 2081044, 5 Dec 2024](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2081044) | **verified (primary)** |
| Cold storage | **8,815 cold storages, 402.18 lakh MT** as of 30 June 2025 | [PIB PRID 2172351, 28 Sep 2025](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2172351) | **verified (primary)** |
| Total economic loss | ₹1,52,790 crore (US$18.5 bn) for 2020-21; fruits and vegetables ₹57,004 crore | MoFPI figures reported 2024-25 | verified (primary annexure + reported) |
| Afresh | Raised $34M (21 Apr 2026); "up to 25 %" shrink reduction | [PR Newswire, 21 Apr 2026](https://www.prnewswire.com/news-releases/afresh-raises-34m-to-scale-ai-across-the-grocery-industry--driving-fresher-food-stronger-margins-and-less-waste-302747794.html) | **company-reported** |
| Celcius Logistics | **Raised ₹250 crore** (Series B, announced 6 May 2025); not "₹250 crore equity" | [Entrepreneur India, 6 May 2025](https://india.entrepreneur.com/en-in/news-and-trends/celcius-logistics-secures-inr-250-cr-in-series-b-to-expand/491145) | **verified (trade press)** |
| Wasteless | Expiry-based shelf markdowns. Their own case study is Edeka Rhein-Ruhr fresh meat, 47-74 % within the covered assortment. The "40 % at Edeka Hamburg" figure is secondhand only and is not used | [Wasteless case study](https://wasteless.com/success/edeka-achieves-dramatic-waste-reduction-and-margin-gains-with-wasteless-ai-powered-markdowns) | **company-reported** (40 % Hamburg: **unverified**) |
| Agmarknet prices | Not obtained: data.gov.in needs a registered API key. Practice prices come from a static table | [dataset](https://www.data.gov.in/resource/variety-wise-daily-market-prices-data-commodity) · `docs/DATABASE.md` §9 | **unverified** |

How to say the tomato numbers: the 3.25 % is a share of tomato *output*, not a share of the loss; the ₹5,921 crore covers all post-harvest stages, not the market-stage slice.

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
| Discount / markdown rules (tiers, caps, elasticity) | our own rule (`docs/ARCHITECTURE.md` §10) | none | own schema; confirm against organizer data |
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
| Markdown tiers and thresholds: `DISCOUNT_RISK_BREAKS` (0.10, 0.30, 0.50), `DISCOUNT_TIERS` (0, 10, 20, 35 %), `DISCOUNT_TIME_TRIGGER_H` (24) | `config.py` | confirm when published |
