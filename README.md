# FreshRoute

**Wild Bugs Hackathon 2026** · team of 3 · 20-hour build

FreshRoute is a hub-level decision tool for perishable produce. Given batches with remaining shelf life, destinations with demand and delivery windows, and vehicles with capacities, it decides **which batch goes where, when, and at what markdown**.

- **Spine:** shelf-life feasibility pre-filter → allocation MILP (HiGHS) → disclosed tiered markdown rule, scored by one seeded simulator and checked by an independent validator.
- **Surface:** a FastAPI service over the engine's own output files, and a React dashboard that renders them.
- **A+ add-ons (each behind a flag):** Monte Carlo stress test with P10–P90 bands, event-driven replan with a diff view, newsvendor demand target. An LLM narrator is stretch only; it never decides.

> **Status:** Phases 0–2 built (gate G2 passed on synthetic data): validator, simulator, metrics, feasibility, MILP (full objective, C6 balance, FEFO warm start), baselines fifo / fefo / last_day_50, `milp_markdown`, calibrated generator, attribution ladder + waterfall (`freshroute ladder`), determinism test, perf harness, scoreboard tab, reason-card templates, dispatch-sheet skeleton. C-06 (organizer baseline) is blocked on the organizer doc. Sections marked *TBD* are filled by the tasks named next to them.
> **In flight:** the toolchain/UI refactor (`docs/TODO.md` Phase 2.5, RF-00 … RF-07): uv for Python, and Streamlit replaced by `backend/` (FastAPI) + `frontend/` (React). The engine is untouched by it.
> **Data:** practice scenarios are **synthetic** and always labelled so. Real-world loss statistics are context, not model inputs.

## Documentation

| Doc | Purpose |
|---|---|
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | How the system works: cost model, MILP, markdown, simulator, add-ons, assumption log |
| [`docs/DATABASE.md`](docs/DATABASE.md) | Data contracts: input tables, output files, event schema, organizer mapping |
| [`docs/TODO.md`](docs/TODO.md) | Schedule, tasks, gates, cut list, pitch and Q&A prep |
| [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md) | Team workflow, git rules, code standards, testing |
| [`DECISIONS.md`](DECISIONS.md) | Decision log (`D-xx`) |
| [`AGENTS.md`](AGENTS.md) | Instructions for AI coding assistants working in this repo |
| [`docs/RESEARCH-v1.md`](docs/RESEARCH-v1.md) | Background research and variant comparison (some figures secondhand; see its §H) |

**Rule #1:** if the organizers publish a cost model or dataset format, theirs overrides everything in these docs.

## Quickstart *(TBD — V-04)*

Install (uv owns Python; Node 22+ for the dashboard):

```bash
uv sync                # Python env from uv.lock, including the dev group
npm ci --prefix frontend
```

Commands (see `docs/CONTRIBUTING.md` §4):

```bash
make run-stub    # freshroute run on tests/fixtures/tiny_3batch (full pipeline, prints the 4 KPIs)
make demo        # (V-04, not built yet) the one command every reported number comes from (seed 42)
make api         # FastAPI on http://127.0.0.1:8000 (docs at /docs)
make web         # Vite dev server on http://localhost:5173, proxying /api
make serve       # build the dashboard and serve it from the API — one URL, the demo path
```

## Assumptions and cost-model mapping *(S-02 written on defaults; finalized at V-03)*

The assumption log lives in `docs/ARCHITECTURE.md` §20 and the organizer column mapping template in `docs/DATABASE.md` §8. Both are copied below (S-02). With each *confirm* item marked resolved or open. Every **confirm** item is still open: **no organizer material has been received**, so S-01/S-02 cannot be signed off (see `docs/TODO.md` S-01).

Mapping table, cost-model comparison and assumption log were completed on 2026-10-14 (S-02 mechanical parts). The open half is the organizer sign-off, which is blocked on material we do not have.

## Results *(TBD — V-04)*

To be copied from `make demo` output only. No projected numbers appear here.

## Sources

Verified, secondhand and vendor-reported claims are labelled in `docs/TODO.md` §10 and `docs/RESEARCH-v1.md` §H. Everything below was re-checked against primary sources on **2026-10-14** (PRE-03). These are framing context, never model inputs.

| Figure we may say | Value | Source | Status |
|---|---|---|---|
| Post-harvest loss study | NABCONS for MoFPI, reference year 2020–22, **54 commodities**, **15 agro-climatic zones**, **292 districts**; stages = harvesting, collection, grading/sorting, winnowing/cleaning, drying, packaging, transportation, farm storage, godown, wholesaler, retailer, processing unit, market transport | [PIB PRID 2148529, 25 Jul 2025](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2148529) · [PIB PRID 2151371, 1 Aug 2025](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2151371) · NABCONS study report, §1.3 | **verified (primary)** |
| Tomato loss | **8.37 % farm stage + 3.25 % market stage = 11.62 %** total | PIB PRID 2151371, Annexure-II | **verified (primary)** |
| Onion loss | **5.31 % + 1.96 % = 7.27 %** | PIB PRID 2151371, Annexure-II | **verified (primary)** |
| Loss ranges | Fruits **6.02–15.05 %**, Vegetables **4.87–11.61 %** (guava 15.05 % is the worst fruit) | MoFPI annexure to Lok Sabha USQ 2998, 6 Aug 2026 | **verified (primary)** |
| **Value of tomato post-harvest loss** | **₹5,921.15 crore** (24.59 lakh MT). Onion ₹5,156.32 crore; potato ₹5,733.84 crore | **Lok Sabha Unstarred Q 2138, 12 Feb 2026**, commodity-wise table "as per NABCONS Study (2022)" | **verified (primary)** — and it **is** an annual estimate, so "a year" may be said |
| Total economic loss | ₹1,52,790 crore (US$18.5 bn) for 2020–21, on average wholesale prices of 2019-20/2020-21/2021-22; fruits+vegetables = ₹57,004 crore (37 %) | MoFPI figures reported 2024–25; category split ₹26,001 cr cereals, ₹29,545 cr fruits, ₹27,459 cr vegetables | verified (primary annexure + reported) |
| Cold storage | **8,815 cold storages, 402.18 lakh MT (40.22 MMT)** as of **30 June 2025** | [PIB PRID 2172351, 28 Sep 2025](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2172351) | **verified (primary)** |
| Agmarknet prices | **not obtained.** data.gov.in requires a registered API key; the published sample key returns `Key not authorised` | [dataset](https://www.data.gov.in/resource/variety-wise-daily-market-prices-data-commodity) · procedure in `docs/DATABASE.md` §9 | **open (PRE-02)** |

**How to say the tomato numbers** (unchanged, now checkable): the 3.25 % is a share of tomato *output*, not a share of the loss; ₹5,921.15 crore covers **all** stages, not the market-stage slice alone; "a year" is supportable.

## Organizer mapping

Template from `docs/DATABASE.md` §8. No organizer material has been read yet, so every row is on the `DECISIONS.md` default rule: our own field is used and the row is marked `default applied (no organizer data yet)`. Organizer file/column and transform stay empty until S-01 is done with real material; rule #1 applies the moment it is known.

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
| `events.*` | our own field (`docs/DATABASE.md` §6, A-14) | none | default applied (no organizer data yet) |
| Origin handling cost | our own field: 0 (A-07) | none | default applied (no organizer data yet) |
| Discount / markdown rules (tiers, caps, elasticity) | our own rule (`docs/ARCHITECTURE.md` §10) | none | default applied (no organizer data yet) |
| Spoilage definition and cost | our own definition (`docs/ARCHITECTURE.md` §7) | none | default applied (no organizer data yet) |
| Fulfillment definition | our own definition (`docs/ARCHITECTURE.md` §7) | none | default applied (no organizer data yet) |
| Hard-constraint list (what counts as a violation) | codes in `validator/` as built in F-04 | none | default applied (no organizer data yet) |
| Submission/plan output format (for `organizer_baseline` export) | our own `plan.csv` (`docs/DATABASE.md` §5.2) | none | default applied (no organizer data yet) |

## Open questions (S-01)

From `docs/TODO.md` §3. "Default" answers come from the default rule in `DECISIONS.md`; everything else is OPEN until the organizers' material is read.

> **Status 2026-10-14: all eight are OPEN and unverifiable.** No organizer material exists in the repo or on the team's machines: `data/organizer/` has never been populated, there is no `.env` with organizer credentials, and the team's own problem-understanding note lists the organizers' baseline as an open question ("Is a baseline supplied by the organizers? If so, implement that baseline exactly"). S-01, S-02 and C-06 stay blocked on receipt of the material. The defaults below are what the code does in the meantime, and rule #1 applies the moment the real thing is known.

| # | Question | Answer | Assumption |
|---|---|---|---|
| 1 | Exact cost model (revenue, transport, handling incl. origin, spoilage/disposal, discount accounting) | Default: our `docs/ARCHITECTURE.md` §7; origin handling cost 0. Organizer model overrides when known. | A-07, A-19 |
| 2 | Organizers' baseline: documented procedure and how it is scored | OPEN | none |
| 3 | Submission format for plans; is a scoring/checker script provided | OPEN | none |
| 4 | Hidden scenarios: same file format as the dataset, size, events, horizon | OPEN (event semantics default: `docs/DATABASE.md` §6) | A-14 |
| 5 | Time conventions: epoch, absolute vs daily-repeating windows | Default: absolute hours from day 0 at 00:00 | A-01 |
| 6 | What counts as a hard-constraint violation | Default: the codes in `validator/` as built in F-04 | none |
| 7 | Rules: AI assistants, external data, open-source libraries; pitch length (assumed 3:00), live demo vs video, venue network and hardware | Default for AI assistants / external data: allowed, human owner reviews every merge; if the rules forbid it, stop and flag at the next gate. Libraries, pitch format, venue: OPEN | none |
| 8 | Are rail lanes, P10/P90 columns and events present in the real data | OPEN | none |

Also open in `DECISIONS.md`: horizon end (default: carry-over valued 0, A-06) and whether `data/organizer/` may be committed (default: git-ignored, never committed).

## Cost-model comparison (S-02)

Every coefficient or formula in `docs/ARCHITECTURE.md` §7 that must change if the organizers' model differs. Parameter values live in `config.py` (`docs/ARCHITECTURE.md` §19); formulas live in `costmodel.py`. No organizer cost model has been read.

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

Copy of `docs/ARCHITECTURE.md` §20, complete (A-01 … A-40). Every **confirm** item is still open: no organizer material has been read yet.

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
| A-13 | Stress sampling distributions as in `docs/ARCHITECTURE.md` §14.1 | team |
| A-14 | Event semantics as in `docs/DATABASE.md` §6 | confirm - still open (default in `DECISIONS.md`) |
| A-15 | Base shelf lives are de-rated team assumptions (FAO/UMaine values are temperate cold-storage references) | team |
| A-16 | `overship_slack`, phi, lambda, `EPS_FEFO` defaults as in `docs/ARCHITECTURE.md` §19 | team |
| A-17 | Newsvendor `c_u`, `c_o`, markdown reference and clamp as in `docs/ARCHITECTURE.md` §14.3 | team |
| A-18 | `last_day_50` = FIFO-nearest + `min(50 %, max_discount_pct)` markdown, salvage floor respected | team |
| A-19 | Unshipped stock is penalized as spoilage only if it would expire at origin within the horizon | team |
| A-20 | Practice prices calibrated from Agmarknet modal Rs/quintal / 100; Agmarknet and post-harvest-loss figures are context, never model inputs claimed as "real" batch data | team |
| A-21 | Practice data is calibrated so FIFO market-stage spoilage lands near NABCONS tomato about 3.25 % and onion about 1.96 % (sanity check only; those are market-stage % of production incl. godowns/wholesale/retail/transport). Measured on synthetic `practice` (FIFO): tomato 3.51 %, onion 0.82 % (onion capped by its 1 % handling loss), others 0.85-7.83 %, overall 3.31 % | team |
| A-22 | Markdown tier boundaries: `risk` exactly 0.30 -> 20 % tier and exactly 0.50 -> 20 % tier (the research ranges "0.10-0.30 / 0.30-0.50" overlap at the boundaries) | team |
| A-23 | A shipment arriving after the horizon counts as origin-side stock (expired or carry-over by its expiry vs `24·H`), which keeps mass balance (F-06) | team |
| A-24 | A lot with no discount row for a day has 0 % discount; a day with no price row uses the last earlier price, else 0 (F-06) | team |
| A-25 | Lot expiry uses the plan's `arrival_h` + `usable_life_at_arrival_h` (base realization); travel/RSL perturbation is not implemented until stress testing (F-06) | team |
| A-26 | Fulfillment denominator is every demand-table row, including destinations that received nothing (F-06) | team |
| A-27 | `build_arcs` rejection precedence: `NO_LANE`, `NOT_AVAILABLE`, `RAIL_SLOT`, `WINDOW`, `SHELF_LIFE`, `BEYOND_HORIZON`; a rail slot after the end of dispatch day t is `RAIL_SLOT`, not a delayed dispatch; batch/vehicle origin mismatch is `NO_LANE`; window checks are inclusive within `FLOAT_TOL` (F-02) | team |
| A-28 | `realization` for `build_arcs` is a dict `{"rsl_h": {batch_id: h}, "travel_h": {(origin, dest, mode): h}}`; for `simulate` it is `{"demand_kg": {(dest, commodity, day): kg}}`. Stress testing (AD-03) must confirm or replace both (F-02, F-06) | team |
| A-29 | Usable life is not clamped at 0; `wait_h` decays at store temperature and `handling_h` is consumed 1:1 (F-01) | team |
| A-30 | Practice data uses a static price table (no Agmarknet snapshot: PRE-02 closed on 2026-10-14, no data.gov.in API key), 0.53–1.0 × base shelf life per batch, 80–480 kg batches, 4 trips/vehicle/day, demand p10/p90 = 0.75 / 1.3 × p50, delivery windows spanning the whole horizon, one rail lane per hub with no rail vehicle, fake Bengaluru coordinates. A-20 does not apply until a snapshot exists. Those knobs (`generator.py` top) are calibrated to the NABCONS sanity targets of A-21 with the static price table, not to real batch data (C-10) | team |
| A-31 | The FIFO baseline is naive per §12: it respects physical limits but ignores shelf life and delivery windows, and the validator reports the resulting violations honestly (2 `SHELF_LIFE` on `tiny_3batch`, 15 on `practice`). The `make check` demo-plan step therefore validates the `milp` plan, not FIFO. FIFO and MILP runs carry no markdown (F-07) | team |
| A-32 | Validator recomputes `arrival_h` from dispatch and lane `travel_h_p50`; has no code for beyond-horizon arrivals; derives trips from `trip_id`; cannot import `config.py`, so `OVERSHIP_SLACK` is passed in by the caller and `PCT` conversion for `discount_pct` is local (F-04) | team |
| A-33 | MILP: trip `dispatch_h` is the max of its lines' dispatch hours; a TimeLimit result with all-zero `x` is treated as "no incumbent" and falls to the FEFO-greedy; a missing demand row is a target of 0; origin-expiry test matches the simulator (§13 step 3): `available_from_h + rsl_h / decay(storage_temp_c) ≤ 24·H` (F-03, fixed at C-01) | team |
| A-34 | Markdown: lot stock for risk is `kg` net of handling loss, FEFO residual demand per day; the cap is `min(max_discount_frac, 1 − salvage/price)`; a monotone-forced discount may fall below the salvage floor when a later price is lower (known gap) (F-09) | team |
| A-35 | MILP C6: `T_d = Σ target` over only the `(d, c, arrival_day)` keys some feasible arc reaches; `avg_fill` = mean over destinations with `T_d > 0`; slack `s_d` is in fill-fraction units, penalised at `PENALTY_MULT × max price × T_d`. On `practice` C6 binds: the solve hits the 30 s limit (gap 3.85 %, proven optimal in ~54 s; ~₹79k objective cost of balance). The FEFO-greedy fallback ignores C6 (C-02) | team |
| A-36 | `last_day_50` runs no worth-it test: it writes discounts.csv rows only for lot-days whose remaining life is ≤ 24 h, with `risk`/`tier_base_pct`/`delta_revenue_inr` = 0, discount `min(50, max_discount_pct, salvage cap)` (C-05) | team |
| A-37 | `milp_markdown` discounts are near-inert while the MILP ships ≤ p50 demand (1 of 551 discount rows non-zero on `practice`; KPIs equal `milp`): lots carry almost no surplus for the worth-it test to sell. `build_discounts` keeps lot stock fixed across days, so it can mark down a lot that already sold out; the simulator ignores that row (known gap) (C-11) | team |
| A-38 | The MILP is warm-started with the FEFO-greedy plan (`warmStart=True`), so under its own objective the time-limited incumbent is never worse than the `fefo` baseline; practice-size solves still end at a 1–6 % MIP gap at 30 s. C1 covers every batch, including batches with no feasible arc. `solver.objective_inr` equals the simulator `net_inr` when `overship_slack = 0` (C-04) | team |
| A-39 | G2 "not worse on spoilage" is measured in kg within the horizon. A plan that sells long-life stock the baseline leaves as carry-over shows that stock's handling loss as extra spoilage (generated `small` seed 1: MILP +4.29 kg of onion handling loss vs FEFO while netting +₹17.6k); that one case is an `xfail` in `tests/test_ladder.py`, not hidden (C-04) | team |
| A-40 | Measured, not targets (C-09): at 10× (2,000 batches, 30 vehicles → 1.44 M arcs) `build_arcs` takes 118–141 s and HiGHS returned only after ~4,184 s despite the 30 s cap, so **the cap is not enforced end to end at that size**. Practice solves in 30 s at a 1–6 % gap. The wall-clock limit makes time-limited results load-dependent, so determinism holds only for solves that finish below the limit. Follow-ups: U-02 (scale fallback) and H-02 (determinism re-check; consider a node limit instead of wall time) | team |

## Sign-off

- [ ] Aarush
- [ ] Omcar
- [ ] Pratham

Not signed off. The commit `docs: sign off cost model and contracts` is made by the team once the organizer material has been read and all three agree (`docs/TODO.md` S-02).
