# FreshRoute

**Wild Bugs Hackathon 2026** · team of 3 · 20-hour build

FreshRoute is a hub-level decision tool for perishable produce. Given batches with remaining shelf life, destinations with demand and delivery windows, and vehicles with capacities, it decides **which batch goes where, when, and at what markdown**.

- **Spine:** shelf-life feasibility pre-filter → allocation MILP (HiGHS) → disclosed tiered markdown rule, scored by one seeded simulator and checked by an independent validator.
- **A+ add-ons (each behind a flag):** Monte Carlo stress test with P10–P90 bands, event-driven replan with a diff view, newsvendor demand target. An LLM narrator is stretch only; it never decides.

> **Status:** Phases 0–1 built (skeleton, validator, simulator, metrics, feasibility, FIFO, generator, MILP). Phase 2 in progress: full MILP objective + C6 balance, FEFO / last_day_50 baselines, scoreboard tab, reason-card templates and dispatch-sheet skeleton done; C-06 blocked on the organizer doc. Sections marked *TBD* are filled by the tasks named next to them.
> **Data:** practice scenarios are **synthetic** and always labelled so. Real-world loss statistics are context, not model inputs.

## Documentation

| Doc | Purpose |
|---|---|
| [`Docs/ARCHITECTURE.md`](Docs/ARCHITECTURE.md) | How the system works: cost model, MILP, markdown, simulator, add-ons, assumption log |
| [`Docs/DATABASE.md`](Docs/DATABASE.md) | Data contracts: input tables, output files, event schema, organizer mapping |
| [`Docs/TODO.md`](Docs/TODO.md) | Schedule, tasks, gates, cut list, pitch and Q&A prep |
| [`Docs/CONTRIBUTING.md`](Docs/CONTRIBUTING.md) | Team workflow, git rules, code standards, testing |
| [`DECISIONS.md`](DECISIONS.md) | Decision log (`D-xx`) |
| [`AGENTS.md`](AGENTS.md) | Instructions for AI coding assistants working in this repo |
| [`Docs/RESEARCH-v1.md`](Docs/RESEARCH-v1.md) | Background research and variant comparison (some figures secondhand; see its §H) |

**Rule #1:** if the organizers publish a cost model or dataset format, theirs overrides everything in these docs.

## Quickstart *(TBD — V-04)*

Commands (see `Docs/CONTRIBUTING.md` §4):

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
make setup && make test
make run-stub    # freshroute run on tests/fixtures/tiny_3batch (full pipeline, prints the 4 KPIs)
make demo        # (V-04, not built yet) the one command every reported number comes from (seed 42)
make app         # Streamlit dashboard (shows tests/fixtures/metrics_example.json when outputs/ is empty)
```

## Assumptions and cost-model mapping *(S-02 written on defaults; finalized at V-03)*

The assumption log lives in `Docs/ARCHITECTURE.md` §20 and the organizer column mapping template in `Docs/DATABASE.md` §8. Both are copied in the sections below (S-02) and finalized at V-03, with each *confirm* item marked resolved or open. The copy below stops at A-22; later assumptions (A-23 onward) live in `ARCHITECTURE.md` §20 only until V-03.

## Results *(TBD — V-04)*

To be copied from `make demo` output only. No projected numbers appear here.

## Sources

Verified, secondhand and vendor-reported claims are labelled in `Docs/TODO.md` §10 and `Docs/RESEARCH-v1.md` §H.

## Organizer mapping

Template from `Docs/DATABASE.md` §8. No organizer material has been read yet, so every row is on the `DECISIONS.md` default rule: our own field is used and the row is marked `default applied (no organizer data yet)`. Organizer file/column and transform stay empty until S-01 is done with real material; rule #1 applies the moment it is known.

| Our table.column | Organizer file.column | Transform | Status |
|---|---|---|---|
| `batches.*` (qty, RSL, temp, availability, origin) | our own field | none | default applied (no organizer data yet) |
| `commodities.base_shelf_life_h / ref_temp_c / q10` | our own field | none | default applied (no organizer data yet) |
| `commodities.min_sell_window_h` | our own field | none | default applied (no organizer data yet) |
| `commodities.handling_loss_pct` | our own field | none | default applied (no organizer data yet) |
| `commodities.unit_cost / disposal_cost / salvage_value` | our own field | none | default applied (no organizer data yet) |
| `commodities.price_elasticity / max_discount_pct` | our own field | none | default applied (no organizer data yet) |
| `destinations.receive_cap_kg_day` | our own field | none | default applied (no organizer data yet) |
| `destinations.handling_time_h / handling_cost_inr_kg` | our own field | none | default applied (no organizer data yet) |
| `destinations.window_open_h / window_close_h` (+ `window_mode`) | our own field | none; absolute hours from day 0 at 00:00 (A-01) | default applied (no organizer data yet) |
| `demand.demand_kg_p10/p50/p90` | our own field | none | default applied (no organizer data yet) |
| `prices.*` | our own field | none | default applied (no organizer data yet) |
| `lanes.travel_h_p50/p90` | our own field | none | default applied (no organizer data yet) |
| `lanes.cost_fixed_inr_trip / cost_var_inr_kg` | our own field | none | default applied (no organizer data yet) |
| `lanes.transit_temp_c` | our own field | none | default applied (no organizer data yet) |
| `lanes.departure_slots` (rail) | our own field | none | default applied (no organizer data yet) |
| `vehicles.*` (capacity, trips/day, availability) | our own field | none | default applied (no organizer data yet) |
| `events.*` | our own field (`Docs/DATABASE.md` §6, A-14) | none | default applied (no organizer data yet) |
| Origin handling cost | our own field: 0 (A-07) | none | default applied (no organizer data yet) |
| Discount / markdown rules (tiers, caps, elasticity) | our own rule (`Docs/ARCHITECTURE.md` §10) | none | default applied (no organizer data yet) |
| Spoilage definition and cost | our own definition (`Docs/ARCHITECTURE.md` §7) | none | default applied (no organizer data yet) |
| Fulfillment definition | our own definition (`Docs/ARCHITECTURE.md` §7) | none | default applied (no organizer data yet) |
| Hard-constraint list (what counts as a violation) | codes in `validator/` as built in F-04 | none | default applied (no organizer data yet) |
| Submission/plan output format (for `organizer_baseline` export) | our own `plan.csv` (`Docs/DATABASE.md` §5.2) | none | default applied (no organizer data yet) |

## Open questions (S-01)

From `Docs/TODO.md` §3. "Default" answers come from the default rule in `DECISIONS.md`; everything else is OPEN until the organizers' material is read.

| # | Question | Answer | Assumption |
|---|---|---|---|
| 1 | Exact cost model (revenue, transport, handling incl. origin, spoilage/disposal, discount accounting) | Default: our `Docs/ARCHITECTURE.md` §7; origin handling cost 0. Organizer model overrides when known. | A-07, A-19 |
| 2 | Organizers' baseline: documented procedure and how it is scored | OPEN | none |
| 3 | Submission format for plans; is a scoring/checker script provided | OPEN | none |
| 4 | Hidden scenarios: same file format as the dataset, size, events, horizon | OPEN (event semantics default: `Docs/DATABASE.md` §6) | A-14 |
| 5 | Time conventions: epoch, absolute vs daily-repeating windows | Default: absolute hours from day 0 at 00:00 | A-01 |
| 6 | What counts as a hard-constraint violation | Default: the codes in `validator/` as built in F-04 | none |
| 7 | Rules: AI assistants, external data, open-source libraries; pitch length (assumed 3:00), live demo vs video, venue network and hardware | Default for AI assistants / external data: allowed, human owner reviews every merge; if the rules forbid it, stop and flag at the next gate. Libraries, pitch format, venue: OPEN | none |
| 8 | Are rail lanes, P10/P90 columns and events present in the real data | OPEN | none |

Also open in `DECISIONS.md`: horizon end (default: carry-over valued 0, A-06) and whether `data/organizer/` may be committed (default: git-ignored, never committed).

## Cost-model comparison (S-02)

Every coefficient or formula in `Docs/ARCHITECTURE.md` §7 that must change if the organizers' model differs. Parameter values live in `config.py` (`Docs/ARCHITECTURE.md` §19); formulas live in `costmodel.py`. No organizer cost model has been read.

| Item (ARCHITECTURE §7) | Where | Status |
|---|---|---|
| Decay law `decay(T) = q10 ^ ((T - ref_temp_c) / 10)` and `Q10_DEFAULT` (2.0, unverified convention) | `costmodel.py` / `config.py` | pending organizer material |
| Usable life at arrival: `RSL - wait_h*decay(T_store) - travel_h*decay(T_transit) - handling_h` | `costmodel.py` | pending organizer material |
| Feasibility rule `usable life >= min_sell_window_h` and arrival inside delivery window | `costmodel.py` | pending organizer material |
| Planning travel time `travel_h_p50` | `costmodel.py` | pending organizer material |
| Dispatch hour `DISPATCH_HOUR` (5) | `config.py` | pending organizer material |
| Effective demand `demand * (1 + min(eps*discount, MAX_UPLIFT))` and `MAX_UPLIFT` (0.5) | `costmodel.py` / `config.py` | pending organizer material |
| Sold `min(on_hand_sellable, effective_demand)`, FEFO within destination | `costmodel.py` | pending organizer material |
| Spoiled kg: `handling_loss_frac * delivered` + unsold at expiry + undispatched expiring at origin | `costmodel.py` | pending organizer material |
| Revenue `sum sold * price * (1 - discount)` | `costmodel.py` | pending organizer material |
| Transport `trips * cost_fixed_inr_trip + kg * cost_var_inr_kg` | `costmodel.py` | pending organizer material |
| Handling `kg_delivered * handling_cost_inr_kg`; origin handling = 0 (A-07) | `costmodel.py` | pending organizer material |
| Spoilage cost `spoiled_kg * (unit_cost + disposal_cost - salvage_value)` | `costmodel.py` | pending organizer material |
| Discount cost reported separately, never subtracted twice | `costmodel.py` | pending organizer material |
| Net `Revenue - Transport - Handling - Spoilage cost` | `costmodel.py` | pending organizer material |
| Demand fulfillment `sum min(sold, base_demand) / sum base_demand`; minimum destination fill rate | `costmodel.py` | pending organizer material |
| Spoilage % `spoiled_kg / sum batches.qty_kg * 100` | `costmodel.py` | pending organizer material |
| Feasibility score = hard violations from `validator/` | `validator/` (independent re-implementation) | pending organizer material |
| Carry-over at horizon end (valued 0, A-06) | `costmodel.py` | pending organizer material |
| Markdown tiers and thresholds: `DISCOUNT_RISK_BREAKS` (0.10, 0.30, 0.50), `DISCOUNT_TIERS` (0, 10, 20, 35 %), `DISCOUNT_TIME_TRIGGER_H` (24) | `config.py` | pending organizer material |

## Assumption log

Copy of `Docs/ARCHITECTURE.md` §20. Every **confirm** item is still open: no organizer material has been read yet.

| ID | Assumption | Status |
|---|---|---|
| A-01 | Epoch = 00:00 of day 0; windows are absolute hours unless `scenario.json` says `window_mode = daily` | confirm - still open |
| A-02 | Hub dispatch hour = 05:00 (`DISPATCH_HOUR`) | team |
| A-03 | `remaining_shelf_life_h` is measured at `available_from_h`, in reference-temperature-equivalent hours; wall-clock life at storage temp = RSL / decay(T_store) | confirm - still open (default in `DECISIONS.md`) |
| A-04 | After arrival, life decays 1 h per h | team |
| A-05 | Day-bucket sales: lot sellable on day k iff `arrival_day <= k` and `expiry_h > 24k` | team |
| A-06 | Horizon end: unexpired stock is carry-over, valued 0, not spoiled; reported as `carryover_kg` | confirm - still open |
| A-07 | Origin handling cost = 0 (schema has no origin handling column; research doc mentions "origin + destination") | confirm - still open |
| A-08 | No vehicle return-time modeling; only `max_trips_day` | team |
| A-09 | A trip serves one destination; loads are splittable across batches | team |
| A-10 | `q10 = 2` default, not verified per commodity | team |
| A-11 | Elasticity uplift is linear in discount, capped at `MAX_UPLIFT` | team |
| A-12 | Shelf price = discount of FEFO-head lot at start of day | team |
| A-13 | Stress sampling distributions as in `Docs/ARCHITECTURE.md` §14.1 | team |
| A-14 | Event semantics as in `Docs/DATABASE.md` §6 | confirm - still open (default in `DECISIONS.md`) |
| A-15 | Base shelf lives are de-rated team assumptions (FAO/UMaine values are temperate cold-storage references) | team |
| A-16 | `overship_slack`, phi, lambda, `EPS_FEFO` defaults as in `Docs/ARCHITECTURE.md` §19 | team |
| A-17 | Newsvendor `c_u`, `c_o`, markdown reference and clamp as in `Docs/ARCHITECTURE.md` §14.3 | team |
| A-18 | `last_day_50` = FIFO-nearest + `min(50 %, max_discount_pct)` markdown, salvage floor respected | team |
| A-19 | Unshipped stock is penalized as spoilage only if it would expire at origin within the horizon | team |
| A-20 | Practice prices calibrated from Agmarknet modal Rs/quintal / 100; Agmarknet and post-harvest-loss figures are context, never model inputs claimed as "real" batch data | team |
| A-21 | Practice data is calibrated so FIFO market-stage spoilage lands near NABCONS tomato about 3.25 % and onion about 1.96 % (sanity check only; those are market-stage % of production incl. godowns/wholesale/retail/transport) | team |
| A-22 | Markdown tier boundaries: `risk` exactly 0.30 -> 20 % tier and exactly 0.50 -> 20 % tier (the research ranges "0.10-0.30 / 0.30-0.50" overlap at the boundaries) | team |

## Sign-off

- [ ] Aarush
- [ ] Omcar
- [ ] Pratham

Not signed off. The commit `docs: sign off cost model and contracts` is made by the team once the organizer material has been read and all three agree (`Docs/TODO.md` S-02).
