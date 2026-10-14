# ARCHITECTURE.md

**FreshRoute — Plan A+** (ShelfSense solver spine + stress test + replan) · 20-hour build · team of 3

> Single source of truth for **how the system works**.
> Data shapes → `DATABASE.md` · Who does what and when → `TODO.md` · How we work together → `CONTRIBUTING.md`.
>
> **Rule #1: if the organizers publish a cost model, theirs overrides everything in this file.** Every coefficient and formula below exists so that all policies and baselines are scored identically and so we can practise before the real data arrives. Map every coefficient to the organizers' columns at H0 (see `TODO.md` S-02).

---

## 1. Scope — what "A+" means

**Spine (Variant A, "ShelfSense Solver")** — must be finished and solid before anything else:
1. Synthetic/organizer data loading with integrity checks.
2. Shared cost model + seeded simulator that scores every policy identically.
3. Independent constraint validator.
4. Baselines: organizers' baseline (official), FIFO-nearest, FEFO-greedy, last-day-50%-markdown.
5. Feasibility pre-filter (shelf-life + delivery-window) → allocation MILP on HiGHS.
6. Disclosed tiered markdown rule.
7. Scoreboard, attribution ladder, net-revenue waterfall, reason cards, dispatch sheet.

**A+ add-ons** — each behind a flag, each independently removable. Priority order (and reverse cut order):
1. **Monte Carlo stress test** with P10–P90 bands (~2 h).
2. **Event-driven replan** with frozen dispatches and a diff view (~3 h).
3. **Newsvendor quantile demand target** (~1 h).
4. **LLM narrator / natural-language event box** — stretch only. A template-based narration is the baseline; the LLM is optional polish.

**Explicitly out of scope** (do not start): statsforecast / demand forecasting, the full agentic/Copilot stack (Variant B), DP-optimized markdown (Variant C), OR-Tools routing, live API calls during the demo, a database server, authentication.

Expected rubric result for A+ is ~82–84/100. That is a judgement-based projection from the research, **not a measurement** — never present it as a result.

---

## 2. Rubric → architecture map

| Rubric item (pts) | What earns it | Where it lives |
|---|---|---|
| Spoilage reduction (20) | Feasibility pre-filter removes "doomed" dispatches; FEFO tie-break; markdown clears the tail | `feasibility.py`, `policies/milp.py`, `discount.py` |
| Demand fulfillment (15) | Objective rewards sell-through; balance constraint stops one destination being starved | `policies/milp.py` (C5, C6), `metrics.py` |
| Net economic outcome (20) | Objective is the organizers' cost terms; one cost model for all policies | `costmodel.py`, `simulator.py` |
| Allocation feasibility (15) | Infeasible arcs have no variable; independent validator reports 0 violations | `feasibility.py`, `validator` |
| Robustness & sensitivity (10) | MC bands, q10/ε sensitivity, replan | `stress.py`, `replan.py`, sensitivity harness |
| Engineering & reproducibility (10) | One seeded command, tests, run manifest, fresh-clone test | `cli.py`, `tests/`, `run_manifest.json` |
| Explainability & commercial (10) | Reason cards, dispatch sheet, positioning slide | `reasons.py`, `dispatch_sheet.py`, `frontend/` |

Total = 20+15+20+15+10+10+10 = **100**. The first four rows (70 pts) are deterministic metrics against the organizers' cost model and hidden scenarios: **a correct optimizer plus an honest simulator wins those points; polish does not.**

---

## 3. Design invariants (never violate)

1. **Organizer overrides ours.** All coefficients live in `costmodel.py` / `config.py` / the dataset. No literals elsewhere.
2. **Feasible by construction, verified independently.** Infeasible (batch, destination, vehicle, day) arcs get no decision variable; the independent validator re-checks the final plan.
3. **Validator independence.** `validator` (package `backend/src/validator/`) re-implements the feasibility maths from the spec and imports **only** `freshroute.schema` and `freshroute.io` (plus stdlib/pandas/numpy). A test enforces this.
4. **One simulator scores everything.** FIFO, FEFO, MILP, MILP+markdown, organizer baseline all go through the same `simulator.py` and `costmodel.py`.
5. **Deterministic.** Same scenario + same seed + same flags ⇒ byte-identical `metrics.json` (apart from the timestamp/runtime fields in `run_manifest.json`).
6. **The LLM never decides.** It may translate a sentence into a schema-validated event and narrate metrics JSON it was given. HiGHS decides.
7. **Add-ons are flags, not forks.** `--newsvendor`, `--no-markdown`, `stress`, `replan` can each be switched off without breaking the spine.
8. **Never return "infeasible", never crash on a scenario.** Soft-constraint slacks, solve time limit, and a FEFO-greedy fallback plan (see §9.5).
9. **The UI shows, the engine decides.** `freshroute.api` serves `outputs/` files verbatim and may enqueue an engine run; `frontend/` renders the JSON it is given. Neither computes a KPI (D-18).
10. **Offline demo.** All demo data is local; no live API; backup video queued.
11. **Measured numbers only.** Every number on a slide comes from `make demo` output with a fixed seed. Label synthetic data as synthetic.

---

## 4. System overview

```
 data/scenarios/<name>/*.csv + scenario.json        organizer files ─► adapters/organizer.py
                       │                                                     │
                       └───────────────► io.load_scenario() ◄────────────────┘
                                  (units, pct→fraction, integrity checks)
                                              │
                                    Scenario (pandas tables)
                 ┌────────────────────────────┼──────────────────────────────┐
                 ▼                            ▼                              ▼
          feasibility.py              policies/*                     newsvendor.py (A+)
          (arcs table)        fifo · fefo · last_day_50              demand targets
                 │            organizer_baseline · milp ◄────────────────────┘
                 └──────────────────────► plan.csv + trips.csv
                                              │
                                              ▼
                                  discount.py ──► discounts.csv
                                              │
                                              ▼
 stress.py (A+) ─────► simulator.py ──► sim_ledger.csv ──► metrics.py ──► metrics.json
 replan.py (A+) ──────────┘                                    ▲
                                                               │
                              validator (independent) ──► validation.json
                                              │
                          reasons.py · dispatch_sheet.py ──► reason_cards.json · dispatch_sheet.*
                                              │
                                              ▼
                 freshroute/api/ (FastAPI) ──► serves outputs/ verbatim, may enqueue a run
                                              │
                                              ▼
                 frontend/ (React SPA) ──► renders the JSON it is given, never recomputes a KPI
```

The UI is a **viewer**: it shows what the engine wrote to `outputs/<run_id>/` and triggers engine functions for "Plan" and "Replan" through the API (D-18, D-21). It never computes a KPI itself, which keeps every number traceable to `run_manifest.json`.

---

## 5. Repository layout

```
freshroute/
├── README.md  AGENTS.md  DECISIONS.md
├── docs/                       # ARCHITECTURE.md  DATABASE.md  TODO.md  CONTRIBUTING.md  RESEARCH-v1.md
├── Makefile  pyproject.toml  uv.lock  .python-version  .gitignore      # uv only, no requirements.txt (D-15)
├── data/
│   ├── organizer/              # raw organizer files (gitignored unless rules allow committing)
│   ├── agmarknet/              # cached CSV snapshot (Agmarknet via data.gov.in)
│   └── scenarios/<name>/       # our 8 CSV tables (+ optional geo.csv) + scenario.json
├── backend/                    # everything server-side (D-16)
│   ├── src/freshroute/
│   │   ├── cli.py  config.py  schema.py  io.py  events.py
│   │   ├── costmodel.py  shelflife.py  feasibility.py
│   │   ├── generator.py  discount.py  simulator.py  metrics.py  ladder.py
│   │   ├── stress.py  replan.py  newsvendor.py
│   │   ├── reasons.py  dispatch_sheet.py  narrator.py
│   │   ├── api/                # FastAPI: serves outputs/ verbatim, may enqueue a run (§16, D-18)
│   │   │   └── app.py  data_access.py  routes.py  schemas.py  jobs.py
│   │   ├── adapters/organizer.py
│   │   └── policies/  base.py  fifo.py  fefo.py  last_day_50.py  organizer_baseline.py  milp.py
│   ├── src/validator/          # second top-level package, INDEPENDENT of freshroute logic (D-17)
│   │   └── validate.py  rules.py
│   └── tests/                  # fixtures/tiny_3batch/  fixtures/metrics_example.json  test_*.py
├── frontend/                   # React SPA: Vite + TypeScript + recharts + react-leaflet (D-19)
│   ├── package.json  package-lock.json  vite.config.ts  tsconfig.json  index.html
│   └── src/  main.tsx  App.tsx  api/  components/  pages/  lib/  types.ts
├── scripts/                    # build_prices.py (Agmarknet → prices.csv)
└── outputs/                    # gitignored, EXCEPT outputs/demo_backup/ (committed at freeze)
```

---

## 6. Modules, owners, responsibilities

Owners: **P1** = Optimization lead · **P2** = Simulation, metrics & validation · **P3** = Product, UI & AI/pitch. (Role definitions in `CONTRIBUTING.md`.)

| Module | Owner | Responsibility |
|---|---|---|
| `cli.py`, `config.py`, `schema.py`, `io.py` | P2 | CLI entry points; tunables; column-name constants; CSV loading, unit conversion (`*_pct` → fraction), integrity checks |
| `costmodel.py` | P2 | The only place cost formulas live (see §7) |
| `shelflife.py` | P1 | `decay(T, ref_temp_c, q10)`, `usable_life_at_arrival(...)` |
| `feasibility.py` | P1 | Builds the `arcs` table (feasible and rejected, with reason codes) |
| `policies/milp.py` | P1 | Allocation MILP on HiGHS (§9) |
| `policies/fifo.py`, `fefo.py`, `last_day_50.py`, `organizer_baseline.py` | P2 | Baselines (§12) |
| `discount.py` | P3 | Tiered markdown rule (§10), pure function + tests |
| `simulator.py`, `metrics.py`, `ladder.py` | P2 | Execution, KPIs, attribution ladder, waterfall data |
| `validator` (`backend/src/validator/`) | P2 | Independent constraint checker (§11) |
| `reasons.py` | P1 (fields) / P3 (templates) | Reason-card fields and rendered text |
| `stress.py`, `newsvendor.py` | P2 | Monte Carlo + sensitivity; quantile demand targets |
| `events.py`, `replan.py` | P1 | Event schema (pydantic), apply, freeze, re-solve, diff |
| `generator.py`, `adapters/organizer.py` | P3 | Practice-data generator; organizer-format adapter (P2 owns the *export* of plans in the organizer's submission format) |
| `dispatch_sheet.py`, `narrator.py` | P3 | Dispatch sheet, narration (template first, LLM optional) |
| `api/` (FastAPI) | P2 | HTTP surface over `outputs/` and the run queue; never a KPI (§16, D-18, D-21) |
| `frontend/` (React) | P3 | Dashboard: scoreboard, plan, robustness, replan, trust (§16, D-19) |

Key function contracts (names are the contract; internals are free):

```python
io.load_scenario(path) -> Scenario
shelflife.decay(temp_c, ref_temp_c, q10) -> float
shelflife.usable_life_at_arrival(rsl_h, wait_h, travel_h, handling_h, store_temp_c, transit_temp_c, ref_temp_c, q10) -> float
feasibility.build_arcs(scenario, realization=None) -> DataFrame            # DATABASE.md §4.1
policies.base.Policy.plan(scenario, ctx) -> Plan                           # plan.csv + trips.csv
discount.build_discounts(scenario, plan) -> DataFrame                      # discounts.csv
simulator.simulate(scenario, plan, discounts, realization) -> SimResult    # sim_ledger.csv
metrics.compute(scenario, plan, discounts, sim) -> dict                    # metrics.json
validator.validate.validate(scenario, plan, discounts) -> ValidationReport # validation.json
stress.run(scenario, plan, discounts, n, seed) -> StressResult
replan.replan(scenario, plan, discounts, event) -> ReplanResult
```

---

## 7. Cost model (shared, single source of truth)

**Where it lives:** every formula below is implemented only in `costmodel.py` (shelf-life maths in `shelflife.py`); every parameter value lives in `config.py` (§19) or the dataset. The validator re-implements the maths independently (§11).

All times are **hours from the planning epoch t = 0**. `day(h) = floor(h / 24)`. Money is ₹. Mass is kg.

**Shelf-life decay.** `decay(T) = q10 ^ ((T − ref_temp_c) / 10)`. One hour at temperature T consumes `decay(T)` hours of remaining life. Default `q10 = 2` is a modelling convention we did **not** verify per commodity; it is exposed as a UI slider.

**Usable life at arrival** (hard feasibility):

```
usable_life_at_arrival = RSL_b − wait_h · decay(T_store) − travel_h · decay(T_transit) − handling_h
feasible  ⇔  usable_life_at_arrival ≥ min_sell_window_h(commodity)
             AND arrival_h falls inside the destination's delivery window
```
`wait_h = dispatch_h − available_from_h(batch)`; `travel_h = travel_h_p50` for planning; `handling_h = destinations.handling_time_h`.

**Sales (per destination × commodity × day).**
```
effective_demand = demand × (1 + min(ε · discount, MAX_UPLIFT))
sold             = min(on_hand_sellable, effective_demand)      # FEFO within the destination
```

**Spoiled kg** = `handling_loss_frac × delivered`  +  delivered-but-unsold lots at expiry  +  undispatched stock that expires at origin within the horizon.

**Economics.**
```
Revenue        = Σ sold × price × (1 − discount)
Transport      = Σ trips × cost_fixed_inr_trip + Σ kg × cost_var_inr_kg
Handling       = Σ kg_delivered × handling_cost_inr_kg           (destination; origin handling = 0, see A-07)
Spoilage cost  = Σ spoiled_kg × (unit_cost + disposal_cost − salvage_value)
Discount cost  = Σ sold × price × discount     # REPORTED separately; already netted inside Revenue — NEVER subtracted again
Net            = Revenue − Transport − Handling − Spoilage cost
```

**Demand fulfillment** = `Σ min(sold, base_demand) / Σ base_demand` over (destination, commodity, day), where `base_demand` is the undiscounted demand of the realization. This equals the research doc's `Σ min(delivered_sellable, demand) / Σ demand` with "delivered_sellable" read as "kg available to sell that day". Also report **minimum destination fill rate** (allocation balance).

**Spoilage %** = `spoiled_kg / Σ batches.qty_kg × 100`.

**Feasibility score** = number of **hard** violations reported by `validator` (never by optimizer code).

**Carry-over.** Stock still unexpired at horizon end (at origin or at destinations) is neither spoiled nor valued; it is reported as `carryover_kg` so nothing is hidden (A-06).

### 7.1 Worked feasibility example (unit-test this, P1 + P2)

Commodity: `ref_temp_c = 20`, `q10 = 2`, `min_sell_window_h = 24`. Batch: `RSL = 100 h`, `available_from_h = 0`, `storage_temp_c = 20`, dispatched at `dispatch_h = 5` ⇒ `wait_h = 5`. Destination `handling_time_h = 2`.

| Lane | T_transit | decay | travel_h | life consumed in transit | usable life | ≥ 24 h? |
|---|---|---|---|---|---|---|
| Reefer, short | 10 °C | 2^((10−20)/10) = 0.5 | 12 | 6 | 100 − 5 − 6 − 2 = **87** | yes |
| Ambient, short | 30 °C | 2^((30−20)/10) = 2 | 12 | 24 | 100 − 5 − 24 − 2 = **69** | yes |
| Ambient, long | 30 °C | 2 | 40 | 80 | 100 − 5 − 80 − 2 = **13** | **no** → arc removed |

(Store decay: `20 °C` = `ref_temp_c` ⇒ decay 1 ⇒ wait consumes 5 h.)

---

## 8. Shelf-life feasibility pre-filter (the core trick)

`feasibility.build_arcs()` enumerates candidate arcs `(batch b, destination d, vehicle v, dispatch day t)` and keeps an arc only if **all** hold:

1. `batch.origin_hub == vehicle.origin == lane.origin`, and a lane `(origin, d, vehicle.mode)` exists.
2. `dispatch_h = max(24·t + DISPATCH_HOUR, batch.available_from_h, vehicle.available_from_h)`; for `rail`, `dispatch_h` is moved to the next `departure_slots` hour-of-day on or after that time.
3. `arrival_h = dispatch_h + travel_h_p50`; `arrival_day ≤ horizon_days − 1`.
4. Arrival inside the destination window — `window_mode = absolute`: `window_open_h ≤ arrival_h ≤ window_close_h`; `window_mode = daily`: hour-of-day of `arrival_h` inside `[window_open_h, window_close_h]`.
5. `usable_life_at_arrival ≥ min_sell_window_h` (§7).

Every rejected arc is **kept** in the table with `feasible = false` and a `reject_reason` (`NO_LANE`, `NOT_AVAILABLE`, `RAIL_SLOT`, `WINDOW`, `SHELF_LIFE`, `BEYOND_HORIZON`). Reason cards use these rows ("Delhi arrival leaves 9 h of life, below the 24 h sell window; Pune leaves 41 h").

The MILP builds variables only from `feasible = true` rows. Shelf-life feasibility therefore holds **by construction**, and the model shrinks a lot.

---

## 9. Allocation MILP (`policies/milp.py`)

### 9.1 Sets and variables
- `A` = feasible arcs `(b, d, v, t)`; arc attributes: price at arrival day `p`, lane costs, `usable_life`, `arrival_day`.
- `x[b,d,v,t] ≥ 0` continuous — kg shipped on the arc.
- `n[v,d,t] ∈ ℤ≥0` — trips of vehicle `v` to `d` on day `t` (a trip serves one destination; loads are splittable across batches).
- `u[b] ≥ 0` — kg left unshipped.

### 9.2 Objective (maximize)

```
Σ_A x · ( p·(1 − h_c) − c_var(lane) − hc_d − λ·h_c·s_c + ε_fefo / usable_life )
 − Σ n · c_fixed(lane)
 − Σ_b λ · s_c · e_b · u_b
 − PENALTY · Σ slacks
```
where `h_c = handling_loss_frac`, `s_c = unit_cost + disposal_cost − salvage_value` (per-kg spoilage cost), `hc_d = handling_cost_inr_kg`, `e_b = 1` if unshipped stock of batch `b` would expire at origin within the horizon else `0`, `λ = LAMBDA_SPOIL` (default 1), `ε_fefo/usable_life` = FEFO tie-breaker (must stay small: keep it under 1 % of the smallest per-kg margin; test it).

The coefficients must reproduce the simulator's accounting. **Consistency test (C-04):** with `overship_slack = 0`, markdown off, p50 realization, the simulator's `net_inr` of the MILP plan equals the MILP objective (excluding the tie-break and slack terms) within a small tolerance.

### 9.3 Constraints

| # | Constraint | Notes |
|---|---|---|
| C1 | `Σ_arcs(b) x + u_b = qty_b` | stock balance (equality with `u` absorbs the rest; equivalent to `Σ x ≤ qty`) |
| C2 | `Σ_b x[b,d,v,t] ≤ cap_v · n[v,d,t]` ∀ (v,d,t) | vehicle capacity |
| C3 | `Σ_d n[v,d,t] ≤ max_trips_day_v` ∀ (v,t) | trips per day |
| C4 | `Σ_{c, arcs with arrival_day = a} x ≤ receive_cap_kg_day_d` ∀ (d,a) | receiving capacity, by **arrival** day |
| C5 | `Σ_{arcs of commodity c, arrival_day = a} x ≤ target_{d,c,a} · (1 + overship_slack)` | demand cap; `target` = `demand_kg_p50`, or the newsvendor quantile when `--newsvendor` is on |
| C6 | `fill_d ≥ φ · avg_fill` (soft) | `fill_d = Σ x / Σ target` for destination `d`; `avg_fill` = mean over destinations with positive target. Linear in `x`. |

Indexing note (D-05): the research doc writes the demand cap with dispatch day `t`; demand and receiving capacity physically bind on the **arrival** day, so we index C4/C5 by arrival day.

### 9.4 Soft constraints
`x = 0, u = qty` is always feasible, so only C6 (and any organizer "must-serve"/minimum-fill rule) needs slacks. Each soft constraint gets a non-negative slack with `PENALTY = 10 × max price in the scenario`. Slack usage is written to `run_manifest.json` (`slack_usage`). In replan, residual capacities that go negative after freezing are clamped to 0 and logged.

### 9.5 Solver settings and fallbacks
- Modeling: **PuLP → HiGHS** by default (readable constraints); `scipy.optimize.milp` (HiGHS, SciPy ≥ 1.9) is the fallback if PuLP/highspy won't install. P1 verifies both at S-04 and records the decision (D-02). Verify that time-limit and gap options actually work in the smoke test; do not assume.
- `MILP_TIME_LIMIT_S = 30`; return the incumbent. `MIP_REL_GAP = 0.01` (assumption).
- **No incumbent by the limit** → return the FEFO-greedy plan, set `fallback_used = true` in the manifest, and show a banner in the UI. Never crash.
- **Scale fallback** (hidden data much larger): aggregate batches by `(commodity, origin, RSL bucket of AGG_RSL_BUCKET_H = 6 h)`, solve, split results proportionally back to batches, then re-run the batch-level feasibility check and repair/drop violators. Measure at U-02 and quote the measured size/time, not an estimate.
- Size estimate from the research (200 batches × 8 destinations × 3 days × 3 vehicles → a few thousand variables after filtering, seconds to solve) is an **engineering estimate, not a benchmark**. Confirm on day 0 and at U-02.

### 9.6 Dispatch prioritization
`priority_score = (1 / usable_life_at_arrival_h) × (kg × price)`. The plan lists shipments in descending score; every line shows `slack_h = usable_life_at_arrival_h − min_sell_window_h`.

---

## 10. Disclosed markdown rule (`discount.py`)

Runs **after** allocation (the MILP does not see future discounts). Pure function of `(scenario, plan)` using **p50** demand; the simulator applies the resulting schedule against realized demand.

For each destination × commodity, lots (`lot_id = batch_id@dest_id@arrival_day`) are processed in FEFO order. Expected demand over each lot's remaining life is allocated to earliest-expiry lots first; later lots see only the residual. For lot `ℓ` on day `k`:

1. `risk = 1 − min(1, expected_demand_over_remaining_life / stock)`
2. Tier: `risk < 0.10 → 0 %` · `0.10 ≤ risk < 0.30 → 10 %` · `0.30 ≤ risk ≤ 0.50 → 20 %` · `risk > 0.50 → 35 %` (boundary convention is A-22: the research ranges overlap at 0.30 and 0.50)
3. **Time trigger:** if remaining life ≤ 24 h, step up one tier (0→10→20→35; 35 stays 35).
4. **Caps:** `discount ≤ max_discount_pct`; `price·(1 − discount) ≥ salvage_value` (⇒ `discount ≤ 1 − salvage/price`).
5. **Worth-it test:** apply a tier only if expected Δrevenue > 0, where
   `base_sold = min(S, D)`, `extra_sold = min(S, D·(1 + min(ε·δ, MAX_UPLIFT))) − base_sold`,
   `Δrev = extra_sold · p · (1 − δ) − base_sold · p · δ`.
   If the proposed tier fails, try the next lower tier; if none pass, 0 %.
6. **Monotone:** discounts never decrease over time for a lot (`discount_k = max(discount_{k−1}, candidate_k)`); when monotonicity forces a discount that fails the worth-it test, log `forced_by_monotone = true`.

The shape (early, multi-step ladder rather than one last-day cut) follows the Hoogvliet/Wasteless and S-market ladders reported in the 2026 markdown preprint (arXiv 2608.23046 — a preprint; cite it as such).

Shelf price (D-08): the simulator uses **one shelf price per destination × commodity × day** = the discount of the FEFO-head lot at the start of that day. Lot-level risk is still shown on reason cards.

---

## 11. Independent validator (`backend/src/validator/`)

Inputs: scenario tables, `plan.csv`, `discounts.csv`. Output: `validation.json` with `violations` (hard) and `warnings` (soft).

**Hard violations** (the feasibility score counts these; confirm against the organizers' definition at H0):
`UNKNOWN_ID` · `NEGATIVE_QTY` · `STOCK_OVERDRAW` (Σ shipped > qty) · `NOT_AVAILABLE` (dispatch before `available_from_h`) · `NO_LANE` · `MODE_MISMATCH` · `RAIL_SLOT` · `SHELF_LIFE` · `DELIVERY_WINDOW` · `VEHICLE_CAPACITY` · `VEHICLE_TRIPS_PER_DAY` · `VEHICLE_AVAILABILITY` · `RECEIVING_CAPACITY` · `DISCOUNT_CAP` · `DISCOUNT_BELOW_SALVAGE` · `DISCOUNT_NOT_MONOTONE`.

**Warnings** (reported, not counted): `DEMAND_CAP_EXCEEDED` (over `target·(1+overship_slack)`), `SLACK_USED`, `FALLBACK_PLAN_USED`.

Independence rules: re-implement `decay`/usable-life from §7 (do not import `shelflife.py`); allowed imports are stdlib, pandas, numpy, `freshroute.schema`, `freshroute.io`, `validator` itself. Tests: (a) an AST test fails if the `validator` package imports any other `freshroute` module; (b) for each hard-violation code, inject one known violation into a clean fixture plan and assert exactly that code appears; (c) a randomized test asserts `validator` and `shelflife.py` agree on usable life. The package lives beside `freshroute` in the same src root only so it is importable from an installed console script (D-17); sharing a directory does not weaken the rule.

---

## 12. Baselines and the attribution ladder

| Policy (`--policy`) | Definition |
|---|---|
| `organizer_baseline` | The organizers' documented baseline — **the official comparison**. Implement exactly from their doc. |
| `fifo` | FIFO-nearest: dispatch in arrival order to the closest destination with remaining demand. Respects physical limits (vehicle capacity, trips/day, receiving capacity, demand cap) but does **not** check shelf-life/window feasibility — that is what a naive dispatcher does. Violations it incurs are reported honestly. |
| `fefo` | FEFO-greedy: earliest-expiry batch first, to the highest-margin **feasible** arc (uses `feasibility.py`) that still has capacity, same demand caps as the MILP. This is a strong baseline: the research cites a simulation where FEFO cut expired product by 50 % vs FIFO (secondhand), so beating only FIFO would look like a strawman. |
| `last_day_50` | FIFO-nearest allocation + 50 % markdown when remaining life ≤ 24 h, capped at `min(50 %, max_discount_pct)` and the salvage floor (kept fair on purpose — "is your baseline fair?" is a likely judge question). |
| `milp` | MILP allocation, no markdown. |
| `milp_markdown` | MILP allocation + §10 markdown. **This is "FreshRoute".** |

**Attribution ladder:** `fifo → fefo → milp → milp_markdown`, all on the same scenario/seed/simulator, headline evaluated on the deterministic **base realization** (p50 demand, p50 travel, p50 RSL). It shows where each rupee of improvement comes from.

**Waterfall** (must reconcile exactly): `baseline net → + spoilage cost avoided → + extra sales (at list price) → − extra transport → − extra handling → − discounts given → = FreshRoute net`. Until C-06 lands (organizer doc), the waterfall baseline is `fefo` and `ladder.json.official_baseline` is `null` (`freshroute ladder --scenario X --seed N`, `ladder.py`).
Invariant (unit-tested, tolerance ₹0.01): `baseline_net + Σ deltas = plan_net`. (The research doc's waterfall omitted the handling step; without it the bars would not sum.)

Step definitions (plan P vs baseline B, read from `economics_inr`): spoilage cost avoided = `spoilage_cost_B − spoilage_cost_P`; extra sales (list) = `gross_P − gross_B`; extra transport = `−(transport_P − transport_B)`; extra handling = `−(handling_P − handling_B)`; discounts given = `−(discount_cost_P − discount_cost_B)`. They sum to `net_P − net_B` exactly because `net = gross − discount_cost − transport − handling − spoilage_cost`.

---

## 13. Simulator (`simulator.py`)

Day-bucket execution of a plan under a **realization** (base = p50; stress = sampled).

1. Build shipments from the plan: `arrival_h = dispatch_h + travel_h(realization)`; lot life at arrival `L` from §7 with the realization's RSL and travel; `expiry_h = arrival_h + L` (post-arrival life decays 1 h per h, A-04).
2. For each day `k = 0 … H−1`, per destination × commodity:
   - **Arrivals** with `arrival_day = k`: remove `handling_loss_frac × kg` as spoiled.
   - **Shelf discount** = discount of the FEFO-head lot at the start of the day (from `discounts.csv`).
   - **Sales:** `effective_demand` per §7; sell FEFO from lots with `arrival_day ≤ k` and `expiry_h > 24·k` (A-05).
   - **End of day:** unsold remainder of lots with `expiry_h ≤ 24·(k+1)` → spoiled (`delivered_unsold`).
3. **Origin:** unshipped kg of batch `b` expires at `available_from_h + RSL / decay(T_store)`; if that is ≤ `24·H` → spoiled (`origin_expired`), else carry-over.
4. Lots alive after day `H−1` → carry-over.
5. Everything is written to `sim_ledger.csv` (per destination × commodity × day) and `sim_lots.csv` (per lot); `metrics.py` aggregates them.

The simulator executes the plan; it does **not** enforce windows/capacities (that is the validator's job), so a bad baseline plan shows both its violations and its economic damage.

---

## 14. A+ add-ons

### 14.1 Monte Carlo stress test (`stress.py`)
- `N = 200` scenarios (fallback 50, then 3 named: optimistic/base/stress). Scenario `i` uses `numpy.random.default_rng(base_seed + i)`.
- Sampled: demand per (dest, commodity, day), travel time per lane, RSL per batch. **Plans are evaluated, not re-optimized** per scenario.
- **Paired comparison:** plan and baseline are executed on the *same* sampled realizations (common random numbers).
- Sampling (A-13): demand and RSL via a piecewise-linear inverse CDF through (0.1, p10), (0.5, p50), (0.9, p90), extrapolated at the tails with the end-segment slope and clipped at 0. Travel time: `u ≤ 0.5 → p50`; `0.5 < u ≤ 0.9 → linear p50→p90`; `u > 0.9 →` extrapolated but capped at `1.5 × p90` (delays only; no early arrivals).
- Output: P10/P50/P90 for each KPI for plan and baseline, plus **share of scenarios where the plan beats the baseline** on net ₹ and on spoilage (`stress_summary.json`, `stress.csv`). Realized shortfalls appear as spoilage, not as validator violations (the validator checks the plan against the data it was given).
- **Sensitivity harness:** `q10` (slider), `ε` vs `ε/2`, `overship_slack`, demand ±20 % → `sensitivity.csv`. Required to answer "why trust your elasticity?".

### 14.2 Event-driven replan (`events.py`, `replan.py`)
- Event JSON (schema in `DATABASE.md` §6): `route_delay`, `capacity_drop`, `demand_spike`, `new_order`, `price_shock`. Validated with pydantic.
- Steps: apply event to a copy of the scenario → **freeze** shipments with `dispatch_h ≤ at_h` → build the residual scenario (reduce `qty_b`, `max_trips_day`, receiving capacity and demand caps by frozen consumption; restrict dispatch to `≥ at_h`) → re-solve → write `replan/<event_id>/`.
- The event still affects frozen shipments in transit (e.g. a delay moves their arrival and may break shelf life) — the simulator shows that; they simply cannot be reassigned.
- Diff (`diff.json`): moved batches (batch → old dest/day → new dest/day), changed discounts, ΔKPIs. **ΔKPIs compare "old plan executed in the changed world" vs "replanned"** — the honest do-nothing comparison.
- Invariants (tests): frozen shipments appear unchanged in the new plan; validator reports 0 hard violations; replan ≤ 5 s on the demo scenario (gate G4). Demo narration may only claim the measured time.
- No round-trip or return-time modeling: vehicles are limited only by `max_trips_day` (A-08).

### 14.3 Newsvendor demand target (`newsvendor.py`)
- Per destination × commodity: plan to the demand quantile `q* = c_u / (c_u + c_o)`.
  `c_u = p·(1 − h_c) − c_var − hc_d` (lost margin per kg short, using the cheapest feasible lane's `c_var`);
  `c_o = s_c + p · NEWSVENDOR_MARKDOWN_REF` (spoilage cost + markdown loss per kg left over, `NEWSVENDOR_MARKDOWN_REF = 0.20`, A-17).
- `q*` clamped to `[0.05, 0.95]`; if `c_u ≤ 0` the target is 0. The quantile comes from the same piecewise inverse CDF as §14.1.
- Output is a `demand_target` table; the MILP reads it in place of `demand_kg_p50` (hook `demand_cap_override`, built at C-03). Off by default in the ladder; `--newsvendor` turns it on; an ablation row shows its effect.

### 14.4 Narrator (stretch)
- `narrator.template_narration(diff_json, metrics_json)` is built first (always available, no network).
- Optional LLM: (a) turn a sentence into an event via function calling → pydantic validation → on failure show "I couldn't parse that — pick from these" and the 5-event dropdown; (b) narrate **only** the metrics/diff JSON it is given. Guard: every number in the narration must appear in the supplied JSON (after rounding) or the template narration is used instead. API key via environment variable only.

---

## 15. Explainability

**Reason card** per shipment (`reason_cards.json`, fields in `DATABASE.md` §5.9). Rendered text pattern:
> "Sent to **Pune**, not Delhi: Delhi arrival leaves 9 h of life, below the 24 h sell window; Pune leaves 41 h; margin ₹X/kg. Dispatch priority #3 (slack 17 h)."

Reason codes for the runner-up: `SHELF_LIFE`, `WINDOW`, `CAPACITY_BOUND`, `DEMAND_CAP`, `LOWER_MARGIN`. **Discount card:** "20 % off from day 2: unsold-risk 0.38 → tier 2; still above salvage floor."

**Dispatch sheet:** per-vehicle, priority-ordered, WhatsApp-style text plus CSV (format in `DATABASE.md` §5.10).

---

## 16. Dashboard (`frontend/`, React SPA over `backend/src/freshroute/api/`)

| Area | Contents |
|---|---|
| Sidebar | scenario picker, seed, flags (markdown on/off, newsvendor on/off), `q10` slider, ε multiplier, **Plan** button |
| Scoreboard | 4 KPI tiles (spoilage kg and %, fulfillment %, net ₹, violations: baseline n vs ours), min fill rate, waterfall, attribution ladder, validator panel |
| Plan | priority-ordered dispatch table, reason card drawer, discount cards, shelf-life countdown map (react-leaflet; colour table is the fallback) |
| Robustness | MC fan chart / bands, % scenarios beating baseline, sensitivity table |
| Replan | 5 canned events dropdown (+ NL box if stretch done), apply, diff view, ΔKPIs, narration |
| Trust | assumptions, cost-model coefficients, `run_manifest.json` (seed, git SHA, scenario hash, solver status) |

### 16.1 Layers and the rules between them

```
frontend/ (React, TS)  ──HTTP──►  freshroute/api/ (FastAPI)  ──in-process──►  cli.run / ladder.run_ladder
       renders JSON verbatim            serves outputs/ verbatim                    writes outputs/<run_id>/
```

- **The engine still decides.** The API may *trigger* an engine function and may serve files the engine wrote. It never computes, derives or aggregates a KPI (D-18). The frontend never computes a KPI either; the only arithmetic it may do is a display delta between two stored numbers, and that lives in one helper (`frontend/src/lib/delta.ts`).
- **Read path:** every screen is a projection of a run directory under `outputs/`. Missing files are absent keys, never invented values. The synthetic-data banner is driven by `scenario.json → source` and is always shown when `source = synthetic`.
- **Write path:** `POST /api/runs` enqueues one run and returns immediately (202). One serialized worker thread runs it so two HiGHS solves never compete for the same laptop; the status file `outputs/.api/jobs/<run_id>.json` tells the frontend whether to poll, show the result or show an error (D-21). `metrics.json` on disk is the definition of "done", so state survives an API restart.
- **Endpoint contract:** `DATABASE.md` §11. Types on the frontend mirror it; a field added there is added to `frontend/src/types.ts` in the same change.
- **Dev vs demo:** in development Vite proxies `/api` to `127.0.0.1:8000`; in the demo FastAPI serves `frontend/dist` from the same origin (D-20), so there is one URL, no CORS and nothing to start twice.
- Demo runs live from local data; `outputs/demo_backup/` and the recorded video are the fallbacks.

---

## 17. CLI contract and Makefile

```
freshroute generate  --seed 42 --out data/scenarios/practice_01
freshroute run       --scenario data/scenarios/practice_01 --policy {organizer_baseline,fifo,fefo,last_day_50,milp,milp_markdown}
                     --seed 42 [--newsvendor] [--no-markdown] --out outputs/<run_id>      → metrics.json (+ all run files)
freshroute validate  --scenario … --plan outputs/<run_id>/plan.csv                        → validation.json
freshroute ladder    --scenario … --seed 42                                               → ladder.json, waterfall.json
freshroute stress    --scenario … --policy milp_markdown --n 200 --seed 42                → stress_summary.json, stress.csv
freshroute replan    --scenario … --run outputs/<run_id> --event event.json               → replan/<event_id>/
freshroute demo      --scenario <demo> --seed 42                                          → everything the pitch needs
```

Flag semantics: `--no-markdown` skips the §10 markdown stage, so `--policy milp_markdown --no-markdown` ≡ `--policy milp`; `--newsvendor` swaps the demand cap for the §14.3 target. `run_manifest.json → flags.markdown` records the effective setting.

`make setup · test · check · demo · api · web · serve · run-stub`. `make check` = ruff + pytest + frontend type/build + validate the demo plan. `make demo` is **the one command** every pitch number comes from. (No `make` on Windows? Run the commands written in the Makefile comments.)

Toolchain (D-15): uv owns Python. `uv sync` installs the project plus the dev group from `uv.lock`; `uv run <cmd>` is the only way anything is executed; `uv lock --check` fails if `pyproject.toml` and `uv.lock` disagree; `uv python pin` sets `.python-version` (D-22). There is no `requirements.txt` and no `pip install` in any recipe.

| Target | What it does |
|---|---|
| `make setup` | `uv sync` + `npm ci` in `frontend/` |
| `make test` | `uv run pytest -q` |
| `make check` | ruff + pytest + `npm run build` (tsc) + validate the demo plan |
| `make demo` | the one command behind every reported number (still the CLI, never HTTP) |
| `make api` | `uv run uvicorn freshroute.api.app:app --reload` on `127.0.0.1:8000` |
| `make web` | Vite dev server on `5173`, proxying `/api` |
| `make serve` | build `frontend/dist`, then run the API serving it — **the demo URL is one command** |
| `make run-stub` | `freshroute run --scenario tests/fixtures/tiny_3batch --policy milp --seed 42` |

---

## 18. Reproducibility

- Seeds: generator seed, MC base seed, tie-breaking seed; defaults 42.
- `run_manifest.json` records: `schema_version`, git SHA, seed, policy, flags, scenario path + SHA-256 of the sorted scenario CSV bytes, package versions, solver status, `mip_gap`, `solve_seconds`, `slack_usage`, `fallback_used`, timestamp.
- Determinism test (C-08): run twice → identical `metrics.json`.
- Dependency versions come from `uv.lock` (Python) and `package-lock.json` (Node); both are committed and neither is edited by hand.
- Fresh-clone test (R-01): clone into a new directory on another machine, `make setup && make demo`, compare headline numbers. The clone needs Node 22+ for `npm ci`; the demo laptop checklist (R-02) covers that.
- The API and the frontend are outside the determinism contract: they read run directories and never recompute them, so a given `outputs/` renders identically every time.

---

## 19. Configuration (`config.py`)

| Parameter | Default | Source |
|---|---|---|
| `Q10_DEFAULT` | 2.0 | research doc (unverified convention) — per-commodity value in data wins |
| `DISPATCH_HOUR` | 5 | team assumption (A-02) |
| `LAMBDA_SPOIL` (λ) | 1.0 | team assumption |
| `EPS_FEFO` | 1.0 (₹·h/kg) | team assumption; test it stays < 1 % of smallest margin |
| `OVERSHIP_SLACK` | 0.05 | team assumption |
| `PHI_BALANCE` (φ) | 0.5 | team assumption |
| `MAX_UPLIFT` | 0.5 | team assumption (A-11) |
| `MILP_TIME_LIMIT_S` | 30 | research doc |
| `MIP_REL_GAP` | 0.01 | team assumption |
| `AGG_RSL_BUCKET_H` | 6 | team assumption |
| `PENALTY_MULT` | 10 (× max price) | team assumption |
| `DISCOUNT_RISK_BREAKS` / `DISCOUNT_TIERS` | 0.10, 0.30, 0.50 / 0, 10, 20, 35 % | research doc |
| `DISCOUNT_TIME_TRIGGER_H` | 24 | research doc |
| `MC_N` / `MC_N_FALLBACK` | 200 / 50 | research doc |
| `NEWSVENDOR_CLAMP` | [0.05, 0.95] | team assumption |
| `NEWSVENDOR_MARKDOWN_REF` | 0.20 | team assumption |
| `DEFAULT_SEED` | 42 | research doc (CLI example) |
| `FLOAT_TOL` | 1e-6 | team assumption (kg and h comparisons) |
| `API_HOST` / `API_PORT` | `127.0.0.1` / `8000` | team assumption (D-18) — loopback only; there is no auth (§21) |
| `API_CORS_ORIGINS` | `["http://localhost:5173"]` | team assumption — dev only; the demo is same-origin (D-20) |
| `JOB_WORKERS` | 1 | team assumption (D-21) — solves are serialized so the demo laptop never runs two HiGHS jobs at once |

---

## 20. Assumption log (disclose all of these in the README)

Anything marked **confirm** must be checked against the organizers' documents at H0 and replaced where they differ.

| ID | Assumption | Status |
|---|---|---|
| A-01 | Epoch = 00:00 of day 0; windows are absolute hours unless `scenario.json` says `window_mode = daily` | confirm |
| A-02 | Hub dispatch hour = 05:00 (`DISPATCH_HOUR`) | team |
| A-03 | `remaining_shelf_life_h` is measured at `available_from_h`, in reference-temperature-equivalent hours; wall-clock life at storage temp = RSL / decay(T_store) | confirm |
| A-04 | After arrival, life decays 1 h per h | team |
| A-05 | Day-bucket sales: lot sellable on day k iff `arrival_day ≤ k` and `expiry_h > 24k` | team |
| A-06 | Horizon end: unexpired stock is carry-over, valued 0, not spoiled; reported as `carryover_kg` | confirm |
| A-07 | Origin handling cost = 0 (schema has no origin handling column; research doc mentions "origin + destination") | confirm |
| A-08 | No vehicle return-time modeling; only `max_trips_day` | team |
| A-09 | A trip serves one destination; loads are splittable across batches | team |
| A-10 | `q10 = 2` default, not verified per commodity | team |
| A-11 | Elasticity uplift is linear in discount, capped at `MAX_UPLIFT` | team |
| A-12 | Shelf price = discount of FEFO-head lot at start of day | team |
| A-13 | Stress sampling distributions as in §14.1 | team |
| A-14 | Event semantics as in `DATABASE.md` §6 | confirm |
| A-15 | Base shelf lives are de-rated team assumptions (FAO/UMaine values are temperate cold-storage references) | team |
| A-16 | `overship_slack`, φ, λ, `EPS_FEFO` defaults as in §19 | team |
| A-17 | Newsvendor `c_u`, `c_o`, markdown reference and clamp as in §14.3 | team |
| A-18 | `last_day_50` = FIFO-nearest + `min(50 %, max_discount_pct)` markdown, salvage floor respected | team |
| A-19 | Unshipped stock is penalized as spoilage only if it would expire at origin within the horizon | team |
| A-20 | Practice prices calibrated from Agmarknet modal ₹/quintal ÷ 100; Agmarknet and post-harvest-loss figures are context, never model inputs claimed as "real" batch data | team |
| A-21 | Practice data is calibrated so FIFO market-stage spoilage lands near NABCONS tomato ≈ 3.25 % and onion ≈ 1.96 % (sanity check only; those are market-stage % of production incl. godowns/wholesale/retail/transport). Measured on `practice` (seed 42, FIFO per-commodity `spoilage_pct`): tomato 3.51, onion 0.82, banana 1.65, mango 5.40, potato 0.85, spinach 7.83 (overall 3.31 %); FEFO 2.49 %, MILP 2.63 % overall. Onion is capped by its 1 % handling loss (720 h shelf life never expires in 3 days); tomato hinges on one 0.5 t origin-expired batch, so it is a coarse fit (C-10) | team |
| A-22 | Markdown tier boundaries: `risk` exactly 0.30 → 20 % tier and exactly 0.50 → 20 % tier (the research ranges "0.10–0.30 / 0.30–0.50" overlap at the boundaries) | team |
| A-23 | A shipment arriving after the horizon counts as origin-side stock (expired or carry-over by its expiry vs `24·H`), which keeps mass balance (F-06) | team |
| A-24 | A lot with no discount row for a day has 0 % discount; a day with no price row uses the last earlier price, else 0 (F-06) | team |
| A-25 | Lot expiry uses the plan's `arrival_h` + `usable_life_at_arrival_h` (base realization); travel/RSL perturbation is not implemented until stress testing (F-06) | team |
| A-26 | Fulfillment denominator is every demand-table row, including destinations that received nothing (F-06) | team |
| A-27 | `build_arcs` rejection precedence: `NO_LANE`, `NOT_AVAILABLE`, `RAIL_SLOT`, `WINDOW`, `SHELF_LIFE`, `BEYOND_HORIZON`; a rail slot after the end of dispatch day t is `RAIL_SLOT`, not a delayed dispatch; batch/vehicle origin mismatch is `NO_LANE`; window checks are inclusive within `FLOAT_TOL` (F-02) | team |
| A-28 | `realization` for `build_arcs` is a dict `{"rsl_h": {batch_id: h}, "travel_h": {(origin, dest, mode): h}}`; for `simulate` it is `{"demand_kg": {(dest, commodity, day): kg}}`. Stress testing (AD-xx) must confirm or replace both (F-02, F-06) | team |
| A-29 | Usable life is not clamped at 0; `wait_h` decays at store temperature and `handling_h` is consumed 1:1 (F-01) | team |
| A-30 | Practice data uses a static price table (no Agmarknet snapshot, PRE-02 missed), 0.53–1.0 × base shelf life per batch, 80–480 kg batches, 4 trips/vehicle/day (trip duration not checked; trips are fleet slots), demand p10/p90 = 0.75 / 1.3 × p50, delivery windows spanning the whole horizon, one rail lane per hub with no rail vehicle, fake Bengaluru coordinates. A-20 does not apply to it until PRE-02 is done (F-08). Those knobs (`generator.py` top) are calibrated to the NABCONS sanity targets of A-21 with the static price table, not to real batch data (C-10) | team |
| A-31 | The FIFO baseline is naive per §12: it respects physical limits but ignores shelf life and delivery windows, and the validator reports the resulting violations honestly (2 `SHELF_LIFE` on `tiny_3batch`, 15 on `practice`). The `make check` demo-plan step therefore validates the `milp` plan, not FIFO. FIFO and MILP runs carry no markdown (F-07) | team |
| A-32 | Validator recomputes `arrival_h` from dispatch and lane `travel_h_p50`; has no code for beyond-horizon arrivals; derives trips from `trip_id`; cannot import `config.py`, so `OVERSHIP_SLACK` is passed in by the caller and `PCT` conversion for `discount_pct` is local (F-04) | team |
| A-33 | MILP: trip `dispatch_h` is the max of its lines' dispatch hours; a TimeLimit result with all-zero `x` is treated as "no incumbent" and falls to the FEFO-greedy; a missing demand row is a target of 0; origin-expiry test matches the simulator (§13 step 3): `available_from_h + rsl_h / decay(storage_temp_c) ≤ 24·H` (F-03, fixed at C-01) | team |
| A-34 | Markdown: lot stock for risk is `kg` net of handling loss, FEFO residual demand per day; the cap is `min(max_discount_frac, 1 − salvage/price)`; a monotone-forced discount may fall below the salvage floor when a later price is lower (known gap) (F-09) | team |
| A-35 | MILP C6: `T_d = Σ target` over only the `(d, c, arrival_day)` keys some feasible arc reaches; `avg_fill` = mean over destinations with `T_d > 0`; slack `s_d` is in fill-fraction units, penalised at `PENALTY_MULT × max price × T_d` (= 10 × max price per kg). On `practice` C6 binds: the solve hits the 30 s limit (gap 3.85 %, proven optimal in ~54 s; ~₹79k objective cost of balance). The FEFO-greedy fallback ignores C6 (C-02) | team |
| A-36 | `last_day_50` runs no worth-it test: it writes discounts.csv rows only for lot-days whose remaining life is ≤ 24 h, with `risk`/`tier_base_pct`/`delta_revenue_inr` = 0, discount `min(50, max_discount_pct, salvage cap)`; if a price fell inside the window the salvage floor would win over monotonicity (not seen on current scenarios) (C-05) | team |
| A-37 | `milp_markdown` discounts are near-inert while the MILP ships ≤ p50 demand (1 of 551 discount rows non-zero on `practice`; KPIs equal `milp`): lots carry almost no surplus for the worth-it test to sell. `build_discounts` keeps lot stock fixed across days, so it can mark down a lot that already sold out; the simulator ignores that row (known gap) (C-11) | team |
| A-38 | The MILP is warm-started with the FEFO-greedy plan (`warmStart=True`), so under its own objective the time-limited incumbent is never worse than the `fefo` baseline; practice-size solves still end at a 1–6 % MIP gap at 30 s. C1 covers every batch, including batches with no feasible arc. `solver.objective_inr` = objective at λ = 1 without tie-break and slack terms; it equals the simulator `net_inr` when `overship_slack = 0` (C-04) | team |
| A-39 | G2 "not worse on spoilage" is measured in kg within the horizon. A plan that sells long-life stock the baseline leaves as carry-over shows that stock's handling loss as extra spoilage (generated `small` seed 1: MILP +4.29 kg of onion handling loss vs FEFO while netting +₹17.6k); that one case is an `xfail` in `tests/test_ladder.py`, not hidden (C-04) | team |
| A-40 | Measured, not targets (C-09, this laptop): `python -m freshroute.perf --scale 10` scales batches **and** vehicles ×10 (2,000 batches, 30 vehicles → 1.44 M arcs, 470 k feasible, ~100× practice): `build_arcs` 118–141 s; HiGHS reports TimeLimit but `prob.solve` returned after ~4,184 s (PuLP model hand-off dominates, unprofiled), so the 30 s cap is **not** enforced end to end at that size. Practice (200 batches) solves in 30 s at a 1–6 % gap. The wall-clock limit makes time-limited results load-dependent (practice MILP under CPU contention: 1,421 kg / ₹1,575,013 at gap 7.3 %; quiet: 1,244 kg / ₹1,655,781 at gap 1.4 %), so rule 4 determinism holds only for solves that finish below the limit. Follow-ups: U-02 (scale fallback, batches-only 10×) and H-02 (determinism re-check; consider a node limit instead of wall time) | team |

---

## 21. Failure modes and fallbacks

| Risk | Fallback |
|---|---|
| Hidden-scenario infeasibility | Soft constraints + penalty slacks; report slack usage |
| Solve time on large data | 30 s limit → incumbent → FEFO-greedy plan; aggregation by commodity × RSL bucket |
| Organizer cost model differs | Everything in `costmodel.py`/`config.py`; coefficients read from the dataset |
| Organizer data format differs | `adapters/organizer.py` + mapping table (`DATABASE.md` §8) |
| Units bug (₹/quintal vs ₹/kg, % vs fraction) | Single conversion in `io.py`; unit tests |
| Replan breaks constraints mid-demo | Validator runs inside `replan`; failing replan falls back to precomputed scenario loaded instantly |
| MC too slow | 200 → 50 → 3 named scenarios |
| LLM hallucination | Schema validation, number guard, template narration, dropdown fallback |
| Solver install fails on demo laptop | `outputs/demo_backup/` + recorded video; `make serve` from a previously built `frontend/dist` |
| Frontend fails to build or the API will not start | Recorded video; `make demo` printed scoreboard; `frontend/dist` rebuilt from the lockfile (`npm ci && npm run build`) |
| Node missing on the demo laptop | R-02 checklist covers it; the CLI, `make demo` and every reported number work without the frontend at all |
| Network down at venue | Demo is fully local; nothing calls the internet (the API serves the SPA from disk, so no CDN, no font or map tile is fetched — Leaflet tiles degrade to the colour-table fallback) |

---

## 22. Performance budget (targets to **measure**, not claims)

| Item | Target | Measured at |
|---|---|---|
| `milp_markdown` plan on the demo scenario | ~3 s (hard cap 30 s, incumbent returned) | C-09, U-02 |
| Replan | < 5 s (gate G4); say only the measured time in the pitch | AD-02 |
| MC 200 scenarios (evaluate only) | measure; if too slow, drop to 50 | AD-03 |
| `make demo` end-to-end | team target ~5 min; measure | U-06 |
| `make serve` to first paint | not a budget item; dev-only numbers, never quoted in the pitch | RF-07 |

---

## 23. Decision log

Moved to the repo-root `DECISIONS.md` (D-01 … D-23). Add new decisions there.
