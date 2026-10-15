# ARCHITECTURE.md

> Single source of truth for **how the system works**.
> Data shapes → `DATABASE.md` · Decisions → `DECISIONS.md` · Plain-language explanations of the *why* → `INDEX.md` and the numbered guides.
>
> **Rule #1: if the organizers publish a cost model, theirs overrides everything in this file.** Every coefficient and formula below exists so that all policies and baselines are scored identically and so we can practise before the real data arrives. Map every coefficient to the organizers' columns when their material is available (`DATABASE.md` §8).

---

## 1. Scope — what "A+" means

**Spine (Variant A, "ShelfSense Solver")** — must be finished and solid before anything else:
1. Synthetic/organizer data loading with integrity checks.
2. Shared cost model + seeded simulator that scores every policy identically.
3. Independent constraint validator.
4. Baselines: FIFO-nearest, FEFO-greedy, last-day-50%-markdown (the organizers' baseline is planned, not built: no organizer material exists).
5. Feasibility pre-filter (shelf-life + delivery-window) → allocation MILP on HiGHS, shown while it solves (§16.2).
6. Scoreboard, attribution ladder, net-revenue waterfall, reason cards, dispatch sheet.

**A+ add-ons** — each behind a flag, each independently removable:
1. **Monte Carlo stress test** with P10–P90 bands.
2. **Event-driven replan** with frozen dispatches and a diff view.
3. **Newsvendor quantile demand target**.
4. **LLM narrator / natural-language event box** — stretch only. A template-based narration is the baseline; the LLM is optional polish.

**Explicitly out of scope** (do not start): statsforecast / demand forecasting, the full agentic/Copilot stack (Variant B), DP-optimized markdown (Variant C), OR-Tools routing, live API calls during the demo, a database server, authentication.

Expected rubric result for A+ is ~82–84/100. That is a judgement-based projection from the research, **not a measurement** — never present it as a result.

---

## 2. Rubric → architecture map

| Rubric item (pts) | What earns it | Where it lives |
|---|---|---|
| Spoilage reduction (20) | Feasibility pre-filter removes "doomed" dispatches; FEFO tie-break; the MILP's unshipped-stock penalty | `domain/feasibility.py`, `solvers/milp_model.py` |
| Demand fulfillment (15) | Objective rewards sell-through; balance constraint stops one destination being starved | `policies/milp.py` (C5, C6), `engine/metrics.py` |
| Net economic outcome (20) | Objective is the organizers' cost terms; one cost model for all policies | `domain/costmodel.py`, `engine/simulator.py` |
| Allocation feasibility (15) | Infeasible arcs have no variable; independent validator reports 0 violations | `domain/feasibility.py`, `validator` |
| Robustness & sensitivity (10) | MC bands, q10/ε sensitivity, replan | `runs/stress.py`, `runs/replan.py`, `runs/sensitivity.py`, `runs/frontier.py`, `policies/milp_robust.py` |
| Engineering & reproducibility (10) | One seeded command, tests, run manifest, fresh-clone check | `cli.py`, `runs/runner.py`, `tests/`, `run_manifest.json` |
| Explainability & commercial (10) | Reason cards, dispatch sheet, dashboard | `engine/reasons.py`, `engine/dispatch_sheet.py`, `frontend/` |

Total = 20+15+20+15+10+10+10 = **100**. The first four rows (70 pts) are deterministic metrics against the organizers' cost model and hidden scenarios: **a correct optimizer plus an honest simulator wins those points; polish does not.**

---

## 3. Design invariants (never violate)

1. **Organizer overrides ours.** All coefficients live in `domain/costmodel.py` / `config.py` / the dataset. No literals elsewhere.
2. **Feasible by construction, verified independently.** Infeasible (batch, destination, vehicle, day) arcs get no decision variable; the independent validator re-checks the final plan.
3. **Validator independence.** `validator` (package `backend/src/validator/`) re-implements the feasibility maths from the spec and imports **only** `freshroute.data.schema` and `freshroute.data.io` (plus stdlib/pandas/numpy). A test enforces this.
4. **One simulator scores everything.** FIFO, FEFO, MILP, organizer baseline all go through the same `engine/simulator.py` and `domain/costmodel.py`.
5. **Deterministic.** Same scenario + same seed + same flags ⇒ byte-identical `metrics.json` (apart from the timestamp/runtime fields in `run_manifest.json`).
6. **The LLM never decides.** It may translate a sentence into a schema-validated event and narrate metrics JSON it was given. HiGHS decides.
7. **Add-ons are flags, not forks.** `--newsvendor`, `stress`, `replan` and the show-while-solving run (§16.2) can each be switched off without breaking the spine.
8. **Never return "infeasible", never crash on a scenario.** Soft-constraint slacks, solve time limit, and a FEFO-greedy fallback plan (see §9.5).
9. **The UI shows, the engine decides.** `freshroute.api` serves `outputs/` files verbatim and may enqueue an engine run; `frontend/` renders the JSON it is given. Neither computes a KPI (D-18).
10. **Offline demo.** All demo data is local; no live API; `outputs/demo_backup/` and a recorded video are the fallbacks.
11. **Measured numbers only.** Every reported number comes from `make demo` output with a fixed seed. Label synthetic data as synthetic.

---

## 4. System overview

```
 data/scenarios/<name>/*.csv + scenario.json        organizer files ─► adapters/organizer.py (planned)
                       │                                                     │
                       └───────────────► data.io.load_scenario() ◄────────────────┘
                                  (units, pct→fraction, integrity checks)
                                              │
                                    Scenario (pandas tables)
                 ┌────────────────────────────┼──────────────────────────────┐
                 ▼                            ▼                              ▼
     domain/feasibility.py            policies/*                  engine/newsvendor.py (A+)
          (arcs table)        fifo · fefo · last_day_50              demand targets
                 │            milp                  ◄────────────────────┘
                 └──────────────────────► plan.csv + trips.csv
                                              │
                                              ▼
                             domain/discount.py ──► discounts.csv
                                              │
                                              ▼
 runs/stress.py (A+) ─► engine/simulator.py ─► sim_ledger.csv ─► engine/metrics.py ─► metrics.json
 runs/replan.py (A+) ────────┘                                    ▲
                                                               │
                              validator (independent) ──► validation.json
                                              │
                engine/reasons.py · engine/dispatch_sheet.py ──► reason_cards.json · dispatch_sheet.*
                                              │
                                              ▼
                 freshroute/api/ (FastAPI) ──► serves outputs/ verbatim, may enqueue a run
                                              │
                                              ▼
                 frontend/ (React SPA) ──► renders the JSON it is given, never recomputes a KPI
```

The UI is a **viewer**: it shows what the engine wrote to `outputs/<run_id>/` and triggers engine functions for "Run the optimiser", "Re-plan now" and the stress test through the API (D-18, D-21). It never computes a KPI itself, which keeps every number traceable to `run_manifest.json`.

---

## 5. Repository layout

```
freshroute/
├── README.md  AGENTS.md  DECISIONS.md
├── docs/                       # INDEX.md, numbered guides 00-10, SUBMISSION/DEMO/JUDGE-QA/GLOSSARY/ORGANIZER-SWAP, ARCHITECTURE.md, DATABASE.md, PS.md. (RESEARCH-v1.md, cited below as "the research doc", is not in the repository.)
├── Makefile  pyproject.toml  uv.lock  .python-version  .gitignore      # uv only, no requirements.txt (D-15)
├── data/
│   ├── organizer/              # raw organizer files (gitignored; never created so far)
│   ├── agmarknet/              # empty; planned cache for an Agmarknet snapshot (no API key available)
│   └── scenarios/<name>/       # our 8 CSV tables (+ geo.csv) + scenario.json
├── backend/                    # everything server-side (D-16)
│   ├── src/freshroute/
│   │   ├── cli.py  config.py   # argparse-only CLI; tunables
│   │   ├── data/               # schema.py  io.py  events.py
│   │   ├── domain/             # costmodel.py  shelflife.py  feasibility.py  discount.py
│   │   ├── engine/             # simulator.py  metrics.py  reasons.py  narrator.py  dispatch_sheet.py  newsvendor.py
│   │   ├── policies/           # __init__.py (REGISTRY, get_policy)  base.py  fifo.py  fefo.py  last_day_50.py  milp.py
│   │   │                       # planned: organizer_baseline.py
│   │   ├── solvers/            # milp_model.py  greedy.py  aggregate.py
│   │   ├── runs/               # runner.py  naming.py  progress.py  ladder.py  stress.py  sensitivity.py  replan.py  perf.py
│   │   ├── generator/          # constants.py  geography.py  build.py  (python -m freshroute.generator)
│   │   ├── api/                # FastAPI: serves outputs/ verbatim, may enqueue a run (§16, D-18)
│   │   │   └── app.py  deps.py  data_access.py  schemas.py  jobs.py  routers/  services/
│   │   └── adapters/           # empty package; planned: organizer.py (organizer-format adapter)
│   ├── src/validator/          # second top-level package, INDEPENDENT of freshroute logic (D-17)
│   │   └── validate.py  rules.py
│   └── tests/                  # fixtures/tiny_3batch/  fixtures/metrics_example.json  test_*.py
├── frontend/                   # React SPA: Vite + TypeScript + recharts + Mantine + motion + GSAP (D-19, D-24, D-27)
│   ├── package.json  package-lock.json  vite.config.ts  tsconfig.json  index.html
│   └── src/  main.tsx  App.tsx  api/  components/  pages/  tabs/  lib/  types.ts  theme.ts
├── (scripts/)                  # planned, not created: build_prices.py (Agmarknet → prices.csv)
└── outputs/                    # gitignored, EXCEPT outputs/demo_backup/
```

---

## 6. Modules and responsibilities

| Module | Responsibility |
|---|---|
| `cli.py`, `config.py` | argparse-only CLI (parses, then calls `runs/`); tunables |
| `data/schema.py`, `data/io.py` | Column-name constants; CSV loading, unit conversion (`*_pct` → fraction), integrity checks |
| `domain/costmodel.py` | The only place cost formulas live (see §7) |
| `domain/shelflife.py` | `decay(T, ref_temp_c, q10)`, `usable_life_at_arrival(...)` |
| `domain/feasibility.py` | Builds the `arcs` table (feasible and rejected, with reason codes) |
| `policies/milp.py`, `solvers/milp_model.py` | Allocation MILP on HiGHS (§9); the model build lives in `solvers/milp_model.py` |
| `solvers/greedy.py`, `solvers/aggregate.py` | FEFO-greedy fallback; scale-model aggregation |
| `policies/__init__.py` | `REGISTRY` and `get_policy(name)`; policy classes import lazily |
| `policies/fifo.py`, `fefo.py`, `last_day_50.py` | Baselines (§12); `organizer_baseline.py` is planned, not built |
| `domain/discount.py` | `discounts.csv` columns and per-destination lot construction (§10); the `last_day_50` baseline fills the ledger |
| `engine/simulator.py`, `engine/metrics.py` | Execution, KPIs; the attribution ladder and waterfall data are in `runs/ladder.py` |
| `validator` (`backend/src/validator/`) | Independent constraint checker (§11) |
| `engine/reasons.py` | Reason-card fields and rendered text |
| `runs/stress.py`, `runs/sensitivity.py`, `engine/newsvendor.py` | Monte Carlo and sensitivity; quantile demand targets |
| `data/events.py`, `runs/replan.py` | Event schema (pydantic); apply, freeze, re-solve, diff |
| `generator/` (`constants.py`, `geography.py`, `build.py`) | Synthetic scenario generator (v3, A-47, A-49) |
| `runs/` (`runner.py`, `naming.py`, `progress.py`, `ladder.py`, `stress.py`, `sensitivity.py`, `replan.py`, `perf.py`) | Orchestration layer: single run, run-id naming, show-while-solving publisher (§16.2), ladder, MC, sensitivity, replan, perf harness (`python -m freshroute.runs.perf`); dependencies run one way, cli -> runs -> engine/domain/data (D-31) |
| `adapters/` | Empty package; the organizer-format adapter (`adapters/organizer.py`) is planned |
| `engine/dispatch_sheet.py`, `engine/narrator.py` | Dispatch sheet, narration (template first, LLM optional) |
| `api/` (FastAPI) | HTTP surface over `outputs/` and the run queue; never a KPI (§16, D-18, D-21) |
| `frontend/` (React) | Landing page plus dashboard tabs Results, Today's plan, What if something breaks?, Proof & audit (§16, D-19, D-32) |

Key function contracts (names are the contract; internals are free):

```python
data.io.load_scenario(path) -> Scenario
domain.shelflife.decay(temp_c, ref_temp_c, q10) -> float
domain.shelflife.usable_life_at_arrival(rsl_h, wait_h, travel_h, handling_h, store_temp_c, transit_temp_c, ref_temp_c, q10) -> float
domain.feasibility.build_arcs(scenario, realization=None) -> DataFrame            # DATABASE.md §4.1
policies.base.Policy.plan(scenario, ctx) -> Plan                           # plan.csv + trips.csv
engine.simulator.simulate(scenario, plan, discounts, realization=None) -> dict    # sim_ledger.csv
engine.metrics.compute(scenario, plan, discounts, sim) -> dict                    # metrics.json
validator.validate.validate(scenario, plan, discounts, overship_slack) -> ValidationReport   # validation.json
runs.stress.run_stress(scenario, policy, n, seed, out, named) -> Path           # stress.csv, stress_summary.json
runs.replan.replan(scenario, plan, trips, discounts, event, *, run_id, seed) -> dict
runs.replan.replan_run(run_dir, event, out=None) -> Path                        # replan/<event_id>/
```

---

## 7. Cost model (shared, single source of truth)

**Where it lives:** every formula below is implemented only in `domain/costmodel.py` (shelf-life maths in `domain/shelflife.py`); every parameter value lives in `config.py` (§19) or the dataset. The validator re-implements the maths independently (§11).

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
COGS           = Σ sold × unit_cost_inr_kg                     (costmodel.cost_of_goods_sold, A-48)
Transport      = Σ trips × cost_fixed_inr_trip + Σ kg × cost_var_inr_kg
Handling       = Σ kg_delivered × handling_cost_inr_kg           (destination; origin handling = 0, see A-07)
Spoilage cost  = Σ spoiled_kg × (unit_cost + disposal_cost − salvage_value)
Discount cost  = Σ sold × price × discount     # REPORTED separately; already netted inside Revenue — NEVER subtracted again
Net            = Revenue − COGS − Transport − Handling − Spoilage cost
```

**Demand fulfillment** = `Σ min(sold, base_demand) / Σ base_demand` over (destination, commodity, day), where `base_demand` is the undiscounted demand of the realization. This equals the research doc's `Σ min(delivered_sellable, demand) / Σ demand` with "delivered_sellable" read as "kg available to sell that day". Also report **minimum destination fill rate** (allocation balance).

**Spoilage %** = `spoiled_kg / Σ batches.qty_kg × 100`.

**Feasibility score** = number of **hard** violations reported by `validator` (never by optimizer code).

**Procurement accounting (D-28, A-48).** Stock is bought at `unit_cost_inr_kg`. Sold kg carry it as cost of goods sold; spoiled kg carry it inside the spoilage cost (`unit_cost + disposal − salvage`); stock still alive at horizon end is inventory held at cost, so it carries neither and is valued 0.

**Carry-over.** Stock still unexpired at horizon end (at origin or at destinations) is neither spoiled nor valued; it is reported as `carryover_kg` so nothing is hidden (A-06).

**Other `domain/costmodel.py` functions.** `demand_uplift(ε, discount) = 1 + min(ε·discount, MAX_UPLIFT)`; `salvage_cap_frac(price, salvage) = 1 − salvage/price` (largest discount that keeps the shelf price at or above salvage); `shipped_margin(price, h_c, unit_cost, c_var, hc_d) = (price − unit_cost)(1 − h_c) − c_var − hc_d` (₹ per shipped kg if it all sells at list; the handling-loss kg are priced separately as spoilage). `domain/feasibility.py` `margin_inr_kg` is `shipped_margin`.

### 7.1 Worked feasibility example (unit-tested)

Commodity: `ref_temp_c = 20`, `q10 = 2`, `min_sell_window_h = 24`. Batch: `RSL = 100 h`, `available_from_h = 0`, `storage_temp_c = 20`, dispatched at `dispatch_h = 5` ⇒ `wait_h = 5`. Destination `handling_time_h = 2`.

| Lane | T_transit | decay | travel_h | life consumed in transit | usable life | ≥ 24 h? |
|---|---|---|---|---|---|---|
| Reefer, short | 10 °C | 2^((10−20)/10) = 0.5 | 12 | 6 | 100 − 5 − 6 − 2 = **87** | yes |
| Ambient, short | 30 °C | 2^((30−20)/10) = 2 | 12 | 24 | 100 − 5 − 24 − 2 = **69** | yes |
| Ambient, long | 30 °C | 2 | 40 | 80 | 100 − 5 − 80 − 2 = **13** | **no** → arc removed |

(Store decay: `20 °C` = `ref_temp_c` ⇒ decay 1 ⇒ wait consumes 5 h.)

Margin for the reefer arc, with price ₹30/kg, `unit_cost` ₹15/kg, `handling_loss_frac` 2.5 %, `cost_var` ₹2/kg, `handling_cost` ₹1/kg: `(30 − 15)(1 − 0.025) − 2 − 1 = 11.625` ₹ per shipped kg. A full hand-computed run (net ₹5,090.25, cost of goods sold ₹17,502.75) is in `backend/tests/fixtures/tiny_3batch/expected/README.md`.

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
Σ_A x · ( (p − unit_cost)·(1 − h_c) − c_var(lane) − hc_d − λ·h_c·s_c + ε_fefo / usable_life )
 − Σ n · c_fixed(lane)
 − Σ_b λ · s_c · e_b · u_b
 − PENALTY · Σ slacks
```
where `h_c = handling_loss_frac`, `s_c = unit_cost + disposal_cost − salvage_value` (per-kg spoilage cost), `hc_d = handling_cost_inr_kg`, `e_b = 1` if unshipped stock of batch `b` would expire at origin within the horizon else `0`, `λ = LAMBDA_SPOIL` (default 1), `ε_fefo/usable_life` = FEFO tie-breaker (must stay small: keep it under 1 % of the smallest per-kg margin; test it).

The first term is `shipped_margin` (§7). The coefficients must reproduce the simulator's accounting, including cost of goods sold. **Consistency test:** with `overship_slack = 0`, markdown off, p50 realization, the simulator's `net_inr` of the MILP plan equals the MILP objective (excluding the tie-break and slack terms) within a small tolerance.

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
- Modeling: **PuLP → HiGHS** by default (readable constraints); `scipy.optimize.milp` (HiGHS, SciPy ≥ 1.9) is the fallback if PuLP/highspy won't install. The decision is recorded in D-02/D-14; the solver smoke test verifies that time-limit and gap options actually work.
- `MILP_TIME_LIMIT_S = 30`; return the incumbent. `MIP_REL_GAP = 0.01` (assumption). The run does not wait for the limit to show a result: the solver reports every better incumbent while it searches (§9.7, §16.2).
- **No incumbent by the limit** → return the FEFO-greedy plan, set `fallback_used = true` in the manifest, and show a banner in the UI. Never crash.
- **Scale model** (`plan_aggregated` in `solvers/aggregate.py`): used when candidate arcs `batches × destinations × vehicles × days > AGG_ARC_THRESHOLD` (`AGG_ARC_THRESHOLD = 20,000`; the `tiny_3batch` and `small` fixtures stay on the batch-level path, `practice` and larger use the pooled model). The unpooled model finds no incumbent in 30 s on `practice` (A-50). Aggregate batches by `(commodity, origin, available_from_h, RSL bucket of AGG_RSL_BUCKET_H = 6 h)`; the pseudo-batch takes the group's total kg, **min** RSL and **max** storage temperature, so any arc feasible for it is feasible for every member (A-41). Vehicles are pooled too (A-46): one lane-class row per `(origin, mode, available_from_h)` carries the arcs, and C2/C3 count trips per capacity class inside it. Solve (same time limit; no incumbent → FEFO-greedy on the aggregate), split each arc's kg back to members pro rata to `qty_kg`, re-run the batch-level feasibility check on the used batches/dests/lane classes and drop lines whose arc is infeasible, hand each class's trips to member vehicles (each within its `max_trips_day`) and fill lines first-fit into them, then run the independent validator; any violation left → FEFO-greedy on the full scenario with `fallback_used = true`. The manifest's `solver.aggregation` block records groups, vehicle classes, aggregate arcs, dropped lines, unassigned kg and validator violations. Scale measurements: A-40.
- The research's size estimate (200 batches × 8 destinations × 3 days × 3 vehicles → a few thousand variables after filtering, seconds to solve) was an **engineering estimate, not a benchmark**; measure with `uv run python -m freshroute.runs.perf` (A-40).

### 9.6 Dispatch prioritization
`priority_score = (1 / usable_life_at_arrival_h) × (kg × price)`. The plan lists shipments in descending score; every line shows `slack_h = usable_life_at_arrival_h − min_sell_window_h`.

### 9.7 Start plan and incumbents
- **Rounded-LP start (A-51).** Before the MIP search the model's trip integers are relaxed, the LP is solved (about 0.1 s on `practice`), and the trip counts are rounded up by LP diving (most fractional third, or half, of the trip variables rounded up per round, re-solving the LP; the better of the two dives wins, a failed round-up falls back to rounding down). The result is a feasible plan handed to HiGHS as its start. FEFO-greedy stays the safety net and is used as the start if it scores higher under the MILP objective. A replan keeps its own warm start (§14.2).
- **Sparse fill balance.** C6 uses one `f_d` (kg to destination `d`) per destination instead of a dense row over all arcs; the model is the same, HiGHS's cut and presolve work is much cheaper (A-51).
- **Incumbent stream.** `milp_model.solve(..., on_incumbent)` receives the start plan and every improving solution HiGHS finds (callback `kCallbackMipImprovingSolution`); policies turn them into plans and `runs.runner.run(on_progress=...)` publishes them (§16.2). Reported figures still come only from the simulator.

---

## 10. Discount ledger (`domain/discount.py`)

FreshRoute's own policy (`milp`) ships **no markdown** (D-33, A-37). Every run also writes `discount_advice.json` (`engine/discount_advice.py`, A-54): for each destination × commodity × day that ends with stock left it tests every cut up to the cap and salvage floor with the simulator's uplift rule and recommends the best one, or says why none pays (elasticity below break-even). `discounts.csv` (DATABASE.md §5.4) still exists as the ledger the simulator, the validator and the reason cards read; only the `last_day_50` baseline (§12) writes non-empty rows. `domain/discount.py` holds the ledger columns and `lots` (lot construction: `lot_id = batch_id@dest_id@arrival_day`, stock net of handling loss), which the simulator and `last_day_50` share.

Shelf price (D-08): the simulator uses **one shelf price per destination × commodity × day** = the discount of the FEFO-head lot at the start of that day. Lot-level risk is still shown on reason cards.

---

## 11. Independent validator (`backend/src/validator/`)

Inputs: scenario tables, `plan.csv`, `discounts.csv`. Output: `validation.json` with `violations` (hard) and `warnings` (soft).

**Hard violations** (the feasibility score counts these; confirm against the organizers' definition once published):
`UNKNOWN_ID` · `NEGATIVE_QTY` · `STOCK_OVERDRAW` (Σ shipped > qty) · `NOT_AVAILABLE` (dispatch before `available_from_h`) · `NO_LANE` · `MODE_MISMATCH` · `RAIL_SLOT` · `SHELF_LIFE` · `DELIVERY_WINDOW` · `VEHICLE_CAPACITY` · `VEHICLE_TRIPS_PER_DAY` · `VEHICLE_AVAILABILITY` · `RECEIVING_CAPACITY` · `DISCOUNT_CAP` · `DISCOUNT_BELOW_SALVAGE` · `DISCOUNT_NOT_MONOTONE`.

That is 16 hard codes (`rules.py`). **Warning** (reported, not counted): `DEMAND_CAP_EXCEEDED` (kg per destination × commodity × arrival day over `p50·(1+overship_slack)`). In a replan, a violation the frozen rows cause on their own is moved to `warnings` as `FROZEN_<code>` (A-43). Slack usage and `fallback_used` are recorded in `run_manifest.json`, not by the validator.

Independence rules: re-implement `decay`/usable-life from §7 (do not import `domain/shelflife.py`); allowed imports are stdlib, pandas, numpy, `freshroute.data.schema`, `freshroute.data.io`, `validator` itself. Tests: (a) an AST test fails if the `validator` package imports any other `freshroute` module; (b) for each hard-violation code, inject one known violation into a clean fixture plan and assert exactly that code appears; (c) a randomized test asserts `validator` and `domain/shelflife.py` agree on usable life. The package lives beside `freshroute` in the same src root only so it is importable from an installed console script (D-17); sharing a directory does not weaken the rule.

---

## 12. Baselines and the attribution ladder

| Policy (`--policy`) | Definition |
|---|---|
| `organizer_baseline` | **Planned, not built.** The organizers' documented baseline would be the official comparison and must be implemented exactly from their doc; no organizer material exists, so the name is recognised by the CLI/API but refuses to run. |
| `fifo` | FIFO-nearest: dispatch in arrival order to the closest destination with remaining demand. Respects physical limits (vehicle capacity, trips/day, receiving capacity, demand cap) but does **not** check shelf-life/window feasibility — that is what a naive dispatcher does. Violations it incurs are reported honestly. |
| `fefo` | FEFO-greedy: earliest-expiry batch first, to the highest-margin **feasible** arc (uses `domain/feasibility.py`) that still has capacity, same demand caps as the MILP. This is a strong baseline: the research cites a simulation where FEFO cut expired product by 50 % vs FIFO (secondhand), so beating only FIFO would look like a strawman. |
| `last_day_50` | FIFO-nearest allocation + 50 % markdown when remaining life ≤ 24 h, capped at `min(50 %, max_discount_pct)` and the salvage floor (kept fair on purpose — "is your baseline fair?" is a likely judge question). |
| `milp` | MILP allocation, no markdown. **This is "FreshRoute"** (D-33). |

**Attribution ladder:** `fifo → fefo → milp`, all on the same scenario/seed/simulator, headline evaluated on the deterministic **base realization** (p50 demand, p50 travel, p50 RSL). It shows where each rupee of improvement comes from.

**Waterfall** (must reconcile exactly): `baseline net → + spoilage cost avoided → + extra sales (at list price) → − cost of extra goods sold → − extra transport → − extra handling → − discounts given → = FreshRoute net` (6 delta steps). Without an organizer baseline, the waterfall baseline is `fefo` and `ladder.json.official_baseline` is `null` (`freshroute ladder --scenario X --seed N`, `runs/ladder.py`).
Invariant (unit-tested, tolerance ₹0.01): `baseline_net + Σ deltas = plan_net`. (The research doc's waterfall omitted the handling step; without it the bars would not sum.)

Step definitions (plan P vs baseline B, read from `economics_inr`): spoilage cost avoided = `spoilage_cost_B − spoilage_cost_P`; extra sales (list) = `gross_P − gross_B`; cost of extra goods sold = `−(cogs_P − cogs_B)`; extra transport = `−(transport_P − transport_B)`; extra handling = `−(handling_P − handling_B)`; discounts given = `−(discount_cost_P − discount_cost_B)`. They sum to `net_P − net_B` exactly because `net = gross − discount_cost − cost_of_goods_sold − transport − handling − spoilage_cost`.

---

## 13. Simulator (`engine/simulator.py`)

Day-bucket execution of a plan under a **realization** (base = p50; stress = sampled).

1. Build shipments from the plan: `arrival_h = dispatch_h + travel_h(realization)`; lot life at arrival `L` from §7 with the realization's RSL and travel; `expiry_h = arrival_h + L` (post-arrival life decays 1 h per h, A-04).
2. For each day `k = 0 … H−1`, per destination × commodity:
   - **Arrivals** with `arrival_day = k`: remove `handling_loss_frac × kg` as spoiled.
   - **Shelf discount** = discount of the FEFO-head lot at the start of the day (from `discounts.csv`).
   - **Sales:** `effective_demand` per §7; sell FEFO from lots with `arrival_day ≤ k` and `expiry_h > 24·k` (A-05).
   - **End of day:** unsold remainder of lots with `expiry_h ≤ 24·(k+1)` → spoiled (`delivered_unsold`).
3. **Origin:** unshipped kg of batch `b` expires at `available_from_h + RSL / decay(T_store)`; if that is ≤ `24·H` → spoiled (`origin_expired`), else carry-over.
4. Lots alive after day `H−1` → carry-over.
5. Everything is written to `sim_ledger.csv` (per destination × commodity × day) and `sim_lots.csv` (per lot); `engine/metrics.py` aggregates them.

The simulator executes the plan; it does **not** enforce windows/capacities (that is the validator's job), so a bad baseline plan shows both its violations and its economic damage.

---

## 14. A+ add-ons

### 14.1 Monte Carlo stress test (`runs/stress.py`)
- `N = 200` scenarios (fallback 50, then 3 named: optimistic/base/stress). Scenario `i` uses `numpy.random.default_rng(base_seed + i)`.
- Sampled: demand per (dest, commodity, day), travel time per lane, RSL per batch. **Plans are evaluated, not re-optimized** per scenario.
- **Paired comparison:** plan and baseline are executed on the *same* sampled realizations (common random numbers).
- Sampling (A-13): demand and RSL via a piecewise-linear inverse CDF through (0.1, p10), (0.5, p50), (0.9, p90), extrapolated at the tails with the end-segment slope and clipped at 0. Travel time: `u ≤ 0.5 → p50`; `0.5 < u ≤ 0.9 → linear p50→p90`; `u > 0.9 →` extrapolated but capped at `1.5 × p90` (delays only; no early arrivals).
- Output: P10/P50/P90 for each KPI for plan and baseline, plus **share of scenarios where the plan beats the baseline** on net ₹ and on spoilage (`stress_summary.json`, `stress.csv`). Realized shortfalls appear as spoilage, not as validator violations (the validator checks the plan against the data it was given).
- Implementation (A-42): `freshroute stress` solves the plan and the baseline (`ladder.BASELINE`, `fefo` while there is no organizer baseline) **once** on the base scenario, then re-simulates both under each realization. `--n 50` is the first fallback, `--named` the last (3 fixed quantile sets, `MC_NAMED`). Wall time is dominated by the one time-limited MILP solve; the per-realization simulate + metrics calls are cheap. Reproduce with: `uv run freshroute stress --scenario data/scenarios/practice --seed 42` (A-40's load caveat applies to the plan being stressed).
- **Sensitivity harness:** `q10` (slider), `ε` vs `ε/2`, `overship_slack`, demand ±20 % → `sensitivity.csv`. Required to answer "why trust your elasticity?".

### 14.2 Event-driven replan (`data/events.py`, `runs/replan.py`)
- Event JSON (schema in `DATABASE.md` §6): `route_delay`, `capacity_drop`, `demand_spike`, `new_order`, `price_shock`. Validated with pydantic.
- Steps: apply event to a copy of the scenario → **freeze** shipments with `dispatch_h ≤ at_h` → build the residual scenario (reduce `qty_b`, `max_trips_day`, receiving capacity and demand caps by frozen consumption; restrict dispatch to `≥ at_h`) → re-solve → write `replan/<event_id>/`.
- The event still affects frozen shipments in transit (e.g. a delay moves their arrival and may break shelf life) — the simulator shows that; they simply cannot be reassigned.
- Diff (`diff.json`): moved batches (batch → old dest/day → new dest/day), changed discounts, ΔKPIs. **ΔKPIs compare "old plan executed in the changed world" vs "replanned"** — the honest do-nothing comparison.
- Invariants (tests): frozen shipments appear unchanged in the new plan; validator reports 0 hard violations; replan wall time is bounded by `REPLAN_TIME_LIMIT_S` plus setup (A-43). Demo narration may only claim a time measured on the day.
- As built: the residual model is the §9 MILP with frozen use passed in through `ctx["residual_use"]` — trips per `(vehicle, day)` off C3, kg per `(dest, arrival_day)` off C4, frozen kg per destination counted in the C6 fill — and C5 via `demand_cap_override = p50 − frozen / (1 + overship_slack)`, so frozen + new never exceeds the original cap. Dispatch `≥ at_h` = vehicles' `available_from_h` raised to `at_h` (a new trip may leave at `at_h` itself). The solve is capped at `REPLAN_TIME_LIMIT_S` and warm-started from the old plan's undispatched rows (infeasible arcs dropped) while that start satisfies every constraint, else from the FEFO-greedy. The replanned plan is a plain `milp` plan with an empty `discounts.csv`. Both sides of the ΔKPIs go through `simulate` + `metrics.compute`; the old side keeps the old `discounts.csv`. Details and limits: A-43.
- No round-trip or return-time modeling: vehicles are limited only by `max_trips_day` (A-08).

### 14.3 Newsvendor demand target (`engine/newsvendor.py`)
- Per destination × commodity: plan to the demand quantile `q* = c_u / (c_u + c_o)`.
  `c_u = p·(1 − h_c) − c_var − hc_d` (lost margin per kg short, using the cheapest feasible lane's `c_var`);
  `c_o = s_c + p · NEWSVENDOR_MARKDOWN_REF` (spoilage cost + markdown loss per kg left over, `NEWSVENDOR_MARKDOWN_REF = 0.20`, A-17).
- `q*` clamped to `[0.05, 0.95]`; if `c_u ≤ 0` the target is 0. The quantile comes from the same piecewise inverse CDF as §14.1.
- Output is a `demand_target` table; the MILP reads it in place of `demand_kg_p50` (hook `demand_cap_override`). Off by default in the ladder; `--newsvendor` turns it on; an ablation row shows its effect.

### 14.5 Robust plan (`policies/milp_robust.py`)
- Policy `milp_robust` (flag policy, Rule 9): the §9 MILP solved on a pessimistic copy of the scenario, every batch at `rsl_p10_h` and every lane at `travel_h_p90`, so a shipment is only chosen if it still fits its shelf life and window when the batch is short-lived and the truck is late.
- The chosen lines are then re-timed on the base (p50) arcs (same batch, destination, vehicle, dispatch day), so the simulator, validator and stress test measure it exactly like `milp` (Rule 3). A line feasible at P10/P90 is feasible at p50 (tested); any that is not is dropped and counted in `run_manifest.json → solver.robust.dropped_lines`.
- Trade-off and measurements: A-52. Reproduce: `uv run freshroute stress --scenario data/scenarios/practice --policy milp_robust --seed 42`.

### 14.6 Profit-vs-spoilage frontier (`runs/frontier.py`)
- Re-plans `milp` once per spoilage weight λ in `FRONTIER_LAMBDAS` (ctx `lambda_spoil`, passed to `milp_model.model_data` and `solve`; default `LAMBDA_SPOIL`, so `milp` itself is unchanged) and scores each plan with the one simulator. Writes `frontier.csv` (DATABASE.md §5.12); served by `GET /api/frontier`.
- It answers "why did spoilage not fall more?" with measured points: what each extra kg of spoilage avoided costs in net ₹. Per-point solve cap `FRONTIER_TIME_LIMIT_S` (A-53).

### 14.4 Narrator (stretch)
- `narrator.template_narration(diff_json, metrics_json)` is built first (always available, no network).
- Optional LLM: (a) turn a sentence into an event via function calling → pydantic validation → on failure show "I couldn't parse that — pick from these" and the 5-event dropdown; (b) narrate **only** the metrics/diff JSON it is given. Guard: every number in the narration must appear in the supplied JSON (after rounding) or the template narration is used instead. API key via environment variable only.

---

## 15. Explainability

**Reason card** per shipment (`reason_cards.json`, fields in `DATABASE.md` §5.9). Rendered text pattern:
> "Sent to **Pune**, not Delhi: it would reach Delhi with only 9 h of shelf life left, too little to sell; 41 h of shelf life left on arrival, 17 h to spare, earns ₹X/kg. Loading priority #3."

Reason codes for the runner-up: `SHELF_LIFE`, `WINDOW`, `CAPACITY_BOUND`, `DEMAND_CAP`, `LOWER_MARGIN`. **Discount card** (only for runs that carry discounts, i.e. `last_day_50`): "50 % off from day 2: last 24 h of usable life; still above salvage floor."

**Dispatch sheet:** per-vehicle, priority-ordered, WhatsApp-style text plus CSV (format in `DATABASE.md` §5.10).

---

## 16. Dashboard (`frontend/`, React SPA over `backend/src/freshroute/api/`)

Components are Mantine 9; GSAP 3.12.5 ScrollTrigger drives the landing page's scroll choreography (hero intro/parallax, section reveals, marquee, anchor nav) and motion springs animate the reason-card drawer, KPI count-ups, table rows and the replan diff (D-24, amended by D-27). Recharts draws the charts; the route map is an offline SVG. Every animation respects `prefers-reduced-motion` (static page fallback). The app has two parts switched by URL hash (D-32): `pages/LandingPage.tsx` (narrative) and `pages/Dashboard.tsx` (four tabs, content in `tabs/`). Labels are plain language; uncommon terms carry a hover note (`components/Explain.tsx`), and all display wording (policy names, rule names, term notes) lives in `lib/words.ts`, which holds words only, never numbers. Method, seed, newsvendor and saved runs live under "Advanced settings".

| Part | Contents |
|---|---|
| Landing page | hero, anchor nav (Problem / How it works / Results / Trust), dark toggle, CTA "Open the live demo". Its result numbers are read from `GET /api/ladder` and `GET /api/stress` for the demo run (`practice`, seed 42), never literals; with no run on disk they show as dashes |
| Dashboard header | scenario name, synthetic-data badge, one **Run the optimiser** button (`RunButton.tsx`), "best plan so far" banner while solving (§16.2) |
| 1. Results (`Scoreboard.tsx`) | baseline vs ours on profit after all costs (net ₹), food spoiled (kg, %), orders filled, worst-served market, rule breaks; "Where the spoiled food went" stacked bar from `spoilage_breakdown_kg`; waterfall ("Where the extra profit comes from"), ladder ("Every rule vs FreshRoute"), validator panel ("Independent check") |
| 2. Today's plan (`Plan.tsx`) | route map (offline SVG network over `geo.csv`; colour table is the fallback), truck loading list and driver message (dispatch sheet), reason-card drawer, price-cut (discount) cards, or the "Discount check" list from `GET /api/runs/{id}/discount-advice` when the plan has no cuts (§10, A-54) |
| 3. What if something breaks? (`Replan.tsx`, `Robustness.tsx`) | click a road on the map (or "close a road" from the list) or a market for a demand spike, or pick any of the 5 event types and press "Re-plan now"; diff view, ΔKPIs, narration; Monte Carlo stress bands and share of futures beating the baseline; sensitivity ("What if our assumptions are wrong?"); profit-vs-spoilage frontier scatter from `GET /api/frontier` (§14.6) |
| 4. Proof & audit (`Trust.tsx`) | `run_manifest.json` ("Reproduce this exact result": seed, git SHA, scenario hash, solver status), every `config.py` constant from `GET /api/config`, assumptions |

### 16.1 Layers and the rules between them

```
frontend/ (React, TS)  ──HTTP──►  freshroute/api/ (FastAPI)  ──in-process──►  runs.runner.run / runs.stress.run_stress / runs.replan.replan_run
       renders JSON verbatim            serves outputs/ verbatim                    writes outputs/<run_id>/
```

- **The engine still decides.** The API may *trigger* an engine function and may serve files the engine wrote. It never computes, derives or aggregates a KPI (D-18). The frontend never computes a KPI either; the only arithmetic it may do is a display delta between two stored numbers, and that lives in one helper (`frontend/src/lib/delta.ts`).
- **Read path:** every screen is a projection of a run directory under `outputs/`. Missing files are absent keys, never invented values. The synthetic-data banner is driven by `scenario.json → source` and is always shown when `source = synthetic`.
- **Write path:** `POST /api/runs` enqueues one run and returns immediately (202). One serialized worker thread runs it so two HiGHS solves never compete for the same laptop; the status file `outputs/.api/jobs/<run_id>.json` tells the frontend whether to poll, show the result or show an error (D-21). `metrics.json` on disk is the definition of "done", so state survives an API restart.
- **Endpoint contract:** `DATABASE.md` §11. Types on the frontend mirror it; a field added there is added to `frontend/src/types.ts` in the same change.
- **Dev vs demo:** in development Vite proxies `/api` to `127.0.0.1:8000`; in the demo FastAPI serves `frontend/dist` from the same origin (D-20), so there is one URL, no CORS and nothing to start twice.
- Demo runs live from local data; `outputs/demo_backup/` and the recorded video are the fallbacks.

### 16.2 Show while solving

The "Run the optimiser" button does not wait for the 30 s limit (D-34). `runs.runner.run(..., on_progress=)` starts a worker (`runs/progress.py`) next to the solver: the solver offers the start plan and every improving incumbent; the worker turns the newest offer into a plan, scores it with the normal pipeline (validator, simulator, metrics) and **publishes it only if its simulated net ₹ beats the last published version**. Publishing writes the whole run directory file by file (temp file + rename, `metrics.json` last) and reports `{version, net_inr, final, elapsed_s}`, which the API stores as `progress` in the job file (DATABASE.md §11.3). The dashboard polls the status once a second, reloads the run whenever `version` increases and shows a "best plan so far" banner until the state is `done`; the last version is the solver's own final plan. Scoring one incumbent costs about 0.4 s on `practice`, so it never starves the search. The CLI `run` has no `on_progress` and writes once, as before. Policies other than `milp` publish only the final plan.

---

## 17. CLI contract and Makefile

```
freshroute generate  [names…] [--out data/scenarios]                                      → regenerates the committed synthetic scenarios (default: all)
freshroute run       --scenario data/scenarios/practice --policy {fifo,fefo,last_day_50,milp}
                     --seed 42 [--newsvendor] [--fail-on-violations] [--out outputs/<run_id>] → metrics.json (+ all run files); exit 1 on violations with the flag
freshroute ladder    --scenario … --seed 42 [--newsvendor] [--out …]                      → ladder.json (+ ablation row), waterfall.json
freshroute sensitivity --scenario … --seed 42 [--out …]                                   → sensitivity.csv
freshroute stress    --scenario … --policy milp --n 200 --seed 42 [--named] [--out …] → stress_summary.json, stress.csv
freshroute replan    --run outputs/<run_id> --event event.json [--out …]                   → replan/<event_id>/ (exit 1 on violations)
                     [--scenario … --policy … --seed 42]  creates --run first when it has no plan.csv
freshroute demo      [--scenario <demo>] [--seed 42] [--with-sensitivity] [--out outputs]  → ladder + waterfall (+ sensitivity.csv); exit 1 if the milp plan has violations
```

`--policy organizer_baseline` is accepted by the parser but refuses to run (planned, no organizer material). There is no `freshroute validate` command: the independent validator runs inside `run`, `replan` and the scale model, and writes `validation.json`; `--fail-on-violations` turns its count into the exit code.

Flag semantics: only `last_day_50` writes markdown rows (`run_manifest.json → flags.markdown` records it); `--newsvendor` (MILP policies only) swaps the demand cap for the §14.3 target. `run_manifest.json → flags.markdown` records the effective setting.

`make setup · test · check · demo · api · web · serve · run-stub`. `make check` = ruff + pytest + frontend type/build + validate the demo plan. `make demo` (`uv run freshroute demo`) is **the one command** every reported number comes from. (No `make` on Windows? Run the commands written in the Makefile comments.)

Toolchain (D-15): uv owns Python. `uv sync` installs the project plus the dev group from `uv.lock`; `uv run <cmd>` is the only way anything is executed; `uv lock --check` fails if `pyproject.toml` and `uv.lock` disagree; `uv python pin` sets `.python-version` (Python 3.13, D-22). There is no `requirements.txt` and no `pip install` in any recipe.

| Target | What it does |
|---|---|
| `make setup` | `uv sync` + `npm ci` in `frontend/` |
| `make test` | `uv run pytest -q` |
| `make check` | ruff + pytest + `npm run build` (tsc) + validate the demo plan |
| `make demo` | the one command behind every reported number (`uv run freshroute demo`; still the CLI, never HTTP) |
| `make api` | `uv run uvicorn freshroute.api.app:app --reload` on `127.0.0.1:8000` |
| `make web` | Vite dev server on `5173`, proxying `/api` |
| `make serve` | build `frontend/dist`, then run the API serving it — **the demo URL is one command** |
| `make run-stub` | `freshroute run --scenario backend/tests/fixtures/tiny_3batch --policy milp --seed 42` |

---

## 18. Reproducibility

- Seeds: generator seed, MC base seed, tie-breaking seed; defaults 42.
- `run_manifest.json` records: `schema_version`, git SHA, seed, policy, flags, scenario path + SHA-256 of the sorted scenario CSV bytes, package versions, solver status, `mip_gap`, `solve_seconds`, `slack_usage`, `fallback_used`, timestamp.
- Determinism test: run twice → identical `metrics.json`.
- Dependency versions come from `uv.lock` (Python) and `package-lock.json` (Node); both are committed and neither is edited by hand.
- Fresh-clone check: clone into a new directory on another machine, `make setup && make demo`, compare headline numbers. The clone needs Node 22+ for `npm ci`.
- The API and the frontend are outside the determinism contract: they read run directories and never recompute them, so a given `outputs/` renders identically every time.

---

## 19. Configuration (`config.py`)

| Parameter | Default | Source |
|---|---|---|
| `Q10_DEFAULT` | 2.0 | research doc (unverified convention) — per-commodity value in data wins |
| `DISPATCH_HOUR` | 5 | team assumption (A-02); `scenario.json → dispatch_hour` overrides |
| `LAMBDA_SPOIL` (λ) | 1.0 | team assumption |
| `EPS_FEFO` | 1.0 (₹·h/kg) | team assumption; test it stays < 1 % of smallest margin |
| `OVERSHIP_SLACK` | 0.05 | team assumption |
| `PHI_BALANCE` (φ) | 0.5 | team assumption |
| `MAX_UPLIFT` | 0.5 | team assumption (A-11) |
| `MILP_TIME_LIMIT_S` | 30 | research doc |
| `REPLAN_TIME_LIMIT_S` | 2 | team assumption (A-43) — residual re-solve cap for replan |
| `MIP_REL_GAP` | 0.01 | team assumption |
| `AGG_RSL_BUCKET_H` | 6 | team assumption |
| `AGG_ARC_THRESHOLD` | 20,000 candidate arcs (batches × dests × vehicles × days) | team assumption (A-50) — above it the MILP uses the fleet-pooled scale model of §9.5; the unpooled practice model finds no incumbent in 30 s on v3 data |
| `PENALTY_MULT` | 10 (× max price) | team assumption |
| `DISCOUNT_TIME_TRIGGER_H` | 24 | research doc |
| `LAST_DAY_DISCOUNT_PCT` | 50 | research doc (`last_day_50` baseline, §12) |
| `MC_N` / `MC_N_FALLBACK` | 200 / 50 | research doc |
| `MC_TRAVEL_CAP_MULT` | 1.5 (× p90) | research doc (§14.1 travel cap) |
| `MC_NAMED` | optimistic (0.9, 0.5, 0.9) · base (0.5, 0.5, 0.5) · stress (0.1, 0.9, 0.1) as quantile `u` for (demand, travel, RSL) | team assumption (A-42) |
| `NEWSVENDOR_CLAMP` | [0.05, 0.95] | team assumption |
| `NEWSVENDOR_MARKDOWN_REF` | 0.20 | team assumption |
| `FRONTIER_LAMBDAS` / `FRONTIER_TIME_LIMIT_S` | 0, 1, 10, 30, 100 / 30 s | team assumption (A-53) |
| `SENS_Q10` / `SENS_ELASTICITY_MULT` / `SENS_OVERSHIP_SLACK` / `SENS_DEMAND_MULT` | 1.5, 2, 3 / 1, 0.5 / 0, 0.05, 0.10 / 0.8, 1, 1.2 | team assumption (sensitivity values) |
| `DEFAULT_SEED` | 42 | research doc (CLI example) |
| `DEMO_SCENARIO` / `DEMO_SEED` | `data/scenarios/practice` / 42 | team assumption — what `freshroute demo` and `make demo` run |
| `BASELINE` / `PLAN` | `fefo` / `milp` | ladder and waterfall endpoints; `fefo` stands in for the planned `organizer_baseline` |
| `FLOAT_TOL` | 1e-6 | team assumption (kg and h comparisons) |
| `HOURS_PER_DAY` | 24 | constant (moved here from `domain/feasibility.py`) |
| `SCHEMA_VERSION` | 2 | data format version (`DATABASE.md` §1); 2 = `cost_of_goods_sold` in net (D-28); also checked by the validator |
| `API_VERSION` | 1 | HTTP contract version (`DATABASE.md` §11) |
| `API_HOST` / `API_PORT` | `127.0.0.1` / `8000` | team assumption (D-18) — loopback only; there is no auth (§21) |
| `API_CORS_ORIGINS` | `["http://localhost:5173"]` | team assumption — dev only; the demo is same-origin (D-20) |
| `JOB_WORKERS` | 1 | team assumption (D-21) — solves are serialized so the demo laptop never runs two HiGHS jobs at once |

---

## 20. Assumption log

Anything marked **confirm** must be checked against the organizers' documents once published and replaced where they differ.

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
| A-20 | Practice prices come from a static, report-grounded table (modal ₹/kg from published Agmarknet aggregates); there is no Agmarknet snapshot. Agmarknet and post-harvest-loss figures are context, never model inputs claimed as "real" batch data | team |
| A-21 | NABCONS post-harvest-loss percentages are context for plausibility only; practice spoilage is not fitted to them (A-47). Onion's 1,440 h shelf life never expires inside a 3-day horizon, so its spoilage is handling loss only | team |
| A-22 | Removed with the tiered markdown rule (D-33, A-37): it fixed the tier boundaries at risk 0.30 and 0.50 | team |
| A-23 | A shipment arriving after the horizon counts as origin-side stock (expired or carry-over by its expiry vs `24·H`), which keeps mass balance | team |
| A-24 | A lot with no discount row for a day has 0 % discount; a day with no price row uses the last earlier price, else 0 | team |
| A-25 | Lot expiry uses the plan's `arrival_h` + `usable_life_at_arrival_h` (base realization); under stress the realization perturbs travel and RSL (A-42) | team |
| A-26 | Fulfillment denominator is every demand-table row, including destinations that received nothing | team |
| A-27 | `build_arcs` rejection precedence: `NO_LANE`, `NOT_AVAILABLE`, `RAIL_SLOT`, `WINDOW`, `SHELF_LIFE`, `BEYOND_HORIZON`; a rail slot after the end of dispatch day t is `RAIL_SLOT`, not a delayed dispatch; batch/vehicle origin mismatch is `NO_LANE`; window checks are inclusive within `FLOAT_TOL` | team |
| A-28 | `realization` for `build_arcs` is a dict `{"rsl_h": {batch_id: h}, "travel_h": {(origin, dest, mode): h}}`; for `simulate` it is `{"demand_kg": {(dest, commodity, day): kg}}`, extended under stress by A-42 | team |
| A-29 | Usable life is not clamped at 0; `wait_h` decays at store temperature and `handling_h` is consumed 1:1 | team |
| A-30 | Practice data uses a static price table (no Agmarknet snapshot; `scenario.json → price_source` says so). Trips are fleet slots bounded by `max_trips_day` (A-08); generator v3 sets `max_trips_day` from lane times (A-49). Generator details: A-47, A-49 | team |
| A-31 | The FIFO baseline is naive per §12: it respects physical limits but ignores shelf life and delivery windows, and the validator reports the resulting violations honestly (on `practice` seed 42 FIFO and `last_day_50` have violations while `fefo` and `milp` have 0; read the current counts from `outputs/demo_backup/practice__ladder__s42/ladder.json`). The `make check` demo-plan step therefore validates the `milp` plan on the demo scenario, not FIFO. Only `last_day_50` carries markdown. Reproduce with: `uv run freshroute ladder --scenario data/scenarios/practice --seed 42` | team |
| A-32 | Validator recomputes `arrival_h` from dispatch and lane `travel_h_p50`; has no code for beyond-horizon arrivals; derives trips from `trip_id`; cannot import `config.py`, so `OVERSHIP_SLACK` is passed in by the caller (`overship_slack`) and `PCT` conversion for `discount_pct` is local | team |
| A-33 | MILP: trip `dispatch_h` is the max of its lines' dispatch hours; a TimeLimit result with all-zero `x` is treated as "no incumbent" and falls to the FEFO-greedy; a missing demand row is a target of 0; origin-expiry test matches the simulator (§13 step 3): `available_from_h + rsl_h / decay(storage_temp_c) ≤ 24·H` | team |
| A-34 | Lot stock is `kg` net of handling loss (used by `domain.discount.lots`); the discount cap is `min(max_discount_frac, 1 − salvage/price)` (the `last_day_50` baseline) | team |
| A-35 | MILP C6: `T_d = Σ target` over only the `(d, c, arrival_day)` keys some feasible arc reaches; `avg_fill` = mean over destinations with `T_d > 0`; slack `s_d` is in fill-fraction units, penalised at `PENALTY_MULT × max price × T_d` (= 10 × max price per kg). The balance constraint can bind and cost objective value; the FEFO-greedy fallback ignores C6. Reproduce the solve with: `uv run freshroute run --scenario data/scenarios/practice --policy milp --seed 42` and read `solver` in `run_manifest.json` | team |
| A-36 | `last_day_50` runs no worth-it test: it writes discounts.csv rows only for lot-days whose remaining life is ≤ 24 h, with `risk`/`tier_base_pct`/`delta_revenue_inr` = 0, discount `min(50, max_discount_pct, salvage cap)`; if a price fell inside the window the salvage floor would win over monotonicity (not seen on current scenarios) | team |
| A-37 | The tiered markdown policy `milp_markdown` was removed (D-33): on `practice` it gave KPIs identical to `milp`, because shipped kg stays at or below p50 demand and no lot carries surplus for a discount to clear. Its rule (risk tiers 0 / 10 / 20 / 35 %, 24 h trigger, worth-it test) is in the git history before D-33 | team |
| A-38 | The MILP is warm-started with the FEFO-greedy plan (`warmStart=True`), so under its own objective the time-limited incumbent is never worse than the `fefo` baseline; time-limited solves can still end at a non-zero MIP gap. C1 covers every batch, including batches with no feasible arc. `solver.objective_inr` = objective at λ = 1 without tie-break and slack terms; it equals the simulator `net_inr` when `overship_slack = 0` | team |
| A-39 | "Not worse on spoilage" is measured in kg within the horizon. The MILP's spoilage % can exceed FEFO's because it ships and sells more: handling loss scales with delivered kg, so a plan that moves more stock shows more handling loss while netting more. Compare with: `uv run freshroute ladder --scenario data/scenarios/practice --seed 42` | team |
| A-40 | Scale behaviour is measured with `uv run python -m freshroute.runs.perf --scale 10` (batches and vehicles ×10; `--fleet-scale 1` scales batches only). The wall-clock solver limit makes time-limited results load-dependent, so determinism holds only for solves that finish below the limit; PuLP model hand-off time is not covered by `MILP_TIME_LIMIT_S`. The scale model (A-41, A-46, A-50) exists because the unpooled batch-level model is far too large at 10×. `build_arcs` on the full scenario is a separate cost; reason cards avoid it with scoped arcs (A-44) | team |
| A-41 | Aggregation key adds `available_from_h` to the documented `(commodity, origin, RSL bucket)` and the pseudo-batch takes min RSL / max storage temperature, so its feasible arcs are feasible for every member (wait ≥ 0, same dispatch hour) and the batch-level re-check drops nothing in practice; the cost is that members lose arcs only their own (longer) RSL would allow, and the solver's `objective_inr` is the representative's, not the simulator's net ₹ | team |
| A-42 | Stress confirms A-28's keys and extends `simulate`'s realization with `travel_h` {(origin, dest, mode): h} and `rsl_h` {batch_id: h} (replacing A-25 under stress): each plan line keeps its `dispatch_h`, gets `arrival_h = dispatch_h + sampled travel` and §7 usable life from the sampled RSL; origin expiry uses the sampled RSL; a lot whose arrival day moves keeps its discount rows (renamed to the new `lot_id`). Draws are independent per demand row (sorted dest, commodity, day), lane (sorted origin, dest, mode) and batch (sorted id), drawn in that order from `default_rng(base_seed + i)`; no correlation across rows. Plans are not re-optimised. `fefo` is the baseline while there is no organizer baseline. "Beats" is strict beyond `FLOAT_TOL` (higher net ₹, lower spoilage kg). Named fallback quantiles (`MC_NAMED`) are a team choice: "stress" = low demand, late trucks, short life | team |
| A-43 | Replan. The residual solve is capped at `REPLAN_TIME_LIMIT_S = 2` and is warm-started from the old plan's undispatched rows, so on practice-size scenarios it is a repair of the old plan (drop now-infeasible lines, re-split over-capacity trips) rather than a fresh optimisation; a longer cap solves further but exceeds the replan wall-time budget. Other semantics: capacity / receiving effects apply from `at_h` by table (no time dimension), so violations caused by frozen rows alone are reported as `FROZEN_<code>` warnings, not counted (DATABASE.md 5.13); `route_delay` re-times only rows still travelling at `at_h` in the simulator, but the validator re-times every row on the lane (an already-arrived frozen row may show a `FROZEN_` warning); the do-nothing side keeps the old `discounts.csv` (a re-timed lot that changes `arrival_day` loses its markdown); a no-op event can still move the plan within the MIP gap because the MILP objective is not the simulator's net ₹. Time-limited replans are load-dependent like A-40; determinism is tested on the tiny fixture (solved to the gap). Reproduce with: `uv run freshroute replan --run outputs/<run_id> --event event.json` | team |
| A-44 | Reason cards use scoped arcs: `build_cards` builds arcs only for batches in the plan × all destinations × one vehicle per `(origin, mode, available_from_h)` class (A-46 pooling; alternatives carry no `vehicle_id`, DATABASE.md 5.9, so the representative is invisible). Byte-identical to full arcs on the tiny fixture and the committed scenarios checked; this keeps `freshroute run` fast at 10× scale | team |
| A-45 | Newsvendor details beyond §14.3: `c_var` = cheapest lane into the destination from any origin holding the commodity (mode/vehicle not checked); unreachable or unpriced keys keep the p50 cap; `--newsvendor` only for MILP policies (CLI and API). Scored on the base (p50) realization only, the target cannot pay off there, so its case rests on the stress test, not on base-realization rows. Reproduce with: `uv run freshroute ladder --scenario data/scenarios/practice --seed 42 --newsvendor` | team |
| A-46 | Scale model fleet pooling: vehicles with the same `(origin, mode, available_from_h)` get identical arcs from §6, so the aggregate model keeps one lane-class arc and splits only C2/C3 by capacity class (same lane, same `capacity_kg`; class trips = sum of member `max_trips_day`; vehicles with `max_trips_day = 0` are dropped). This is exact for the aggregate model, not a heuristic: any class plan disaggregates to concrete vehicles round-robin by `vehicle_id` without breaking C2/C3; the batch-level re-check runs against the lane-class row, which shares every arc attribute with its members, and the validator then checks the concrete plan. Replan frozen trips are summed onto their class | team |
| A-47 | Generator v3 (D-29) is tuned for plausibility, not calibrated to NABCONS: shelf-life base hours / q10 / reference temperature per commodity (`generator._COMM`) are set so expiry binds for spinach, tomato, banana and mango while onion and potato do not; remaining shelf life ~ Beta(5, 2) × base with the quality grade derived from it; storage temperature is drawn per commodity; prices = static table × outlet-type premium × a shared per-commodity daily market walk. Plausibility is asserted by the quality tests in `backend/tests/test_generator.py` (travel time follows distance, demand matches supply and is reachable, fleet is physically possible, expiry binds, net margin is in a believable range). NABCONS and Agmarknet figures are context only | team |
| A-48 | Procurement is part of net ₹ (D-28): `net = revenue − cost_of_goods_sold − transport − handling − spoilage_cost`, with `cost_of_goods_sold = sold_kg × unit_cost_inr_kg` (`costmodel.cost_of_goods_sold`). Spoilage cost still equals `unit_cost + disposal − salvage` per spoiled kg; stock alive at horizon end is inventory held at cost (carry-over, valued 0 as in A-06, no COGS). `metrics.json → economics_inr` gains `cost_of_goods_sold`; `schema_version` is 2 | team |
| A-49 | Generator v3 geography, demand and fleet: real node names and coordinates (hubs `HUB1` Kolar, `HUB2` Chikkaballapur; destinations `D1`–`D8` from `generator.DESTS`); road lane time = road km (haversine × 1.3) / 40 km/h + 0.5 h; rail lanes only to destinations ≥ 200 km; outlet type sets the daily delivery window (`window_mode = daily`), price premium, commodity basket and receiving capacity. Demand per commodity ≈ U(0.9, 1.1) × supply, placed only on days some lane can reach the outlet inside its window (no unreachable demand), with lognormal outlet shares capped at 35 %. Fleet: both road modes per hub, capacities 1 / 3 / 5 / 9 t, `max_trips_day = floor(16 / (2 × median lane h))` and at least 1, one rail vehicle per hub that has a rail lane. `price_source = static_table_generator_v3`. Practice = seed 42, 200 batches, 8 destinations, 3 days, 6 road vehicles | team |
| A-50 | The MILP uses the fleet-pooled scale model by default above `AGG_ARC_THRESHOLD = 20,000` candidate arcs (A-46), which includes `practice`. Solution quality versus the unpooled model cannot be compared there: the unpooled model finds no incumbent in 30 s on practice v3 data | team |
| A-51 | MILP start and shape. On `practice` HiGHS finds no usable plan for about 12 s (root cuts), and a FEFO-greedy start scores far below the MILP objective because it ignores C6. So: (a) the trip integers are relaxed, the LP solved and rounded up by diving (best of two dives) to give a feasible start in about 0.1 s; (b) the C6 average-fill row is built from per-destination totals `f_d` instead of one dense row, the same model with much cheaper cuts. Measured on the 200-batch `practice` scenario, seed 42, one machine: first plan after about 1.5 s, a plan above the previous 30 s result after about 7 s, 30 s final net ₹442,214 against ₹395,344 before. Timing varies by machine and load | team |
| A-52 | `milp_robust` plans on `rsl_p10_h` and `travel_h_p90` (§14.5) and is measured on p50 like every policy. Measured on synthetic `practice`, seed 42, one machine: base spoilage 726 kg against `milp` 854 kg, net ₹396,895 against ₹442,214, minimum destination fill 0 % against 52.8 %; under the 200-future stress test it beats FEFO on spoilage kg in 100 % of futures (`milp`: 84.5 %) and on net in 100 %. It is a trade-off, not a replacement: it ships less to protect against bad futures. Reproduce: `uv run freshroute run --scenario data/scenarios/practice --policy milp_robust --seed 42` and the stress command in §14.5 | team |
| A-53 | Frontier weights `FRONTIER_LAMBDAS = (0, 1, 10, 30, 100)` scale the spoilage term of the §9.2 objective only (it is about ₹0.5–1 per kg shipped against margins of ₹10 or more, so λ up to 8 barely moved the plan, measured); the reported KPIs come from the simulator. Each point is a time-limited solve (`FRONTIER_TIME_LIMIT_S = 30`); a 10 s cap gave incumbents too noisy to read as a curve, and even at 30 s a point can sit off the curve because the incumbent, not the optimum, is reported (A-40). Reproduce: `uv run freshroute frontier --scenario data/scenarios/practice --seed 42` | team |
| A-54 | Discount advisor estimate (§10): for a cut `L` on a ledger row, extra kg = `base_demand × (uplift(ε, L) − 1)` capped at the stock left; INR effect = revenue change on all sold kg + (disposal − salvage) on extra kg that would have expired − unit cost on extra kg that would have been carried over (A-06, A-48). It ignores knock-on effects on later days; the simulator remains the only reported number. On `practice` every elasticity is ≤ 1.2, so the advice is 0 % with the break-even reason; a cut pays only where elasticity is high and stock is left | team |

---

## 21. Failure modes and fallbacks

| Risk | Fallback |
|---|---|
| Hidden-scenario infeasibility | Soft constraints + penalty slacks; report slack usage |
| Solve time on large data | 30 s limit → incumbent → FEFO-greedy plan; aggregation by commodity × RSL bucket |
| Organizer cost model differs | Everything in `domain/costmodel.py`/`config.py`; coefficients read from the dataset |
| Organizer data format differs | planned `adapters/organizer.py` (not built) + mapping table (`DATABASE.md` §8) |
| Units bug (₹/quintal vs ₹/kg, % vs fraction) | Single conversion in `data/io.py`; unit tests |
| Replan breaks constraints mid-demo | Validator runs inside `replan` (`freshroute replan` exits 1 on violations; the dashboard shows the error). No precomputed replan is shipped; fall back to the stress results on the same tab |
| MC too slow | 200 → 50 → 3 named scenarios |
| LLM hallucination | Schema validation, number guard, template narration, dropdown fallback |
| Solver install fails on demo laptop | `outputs/demo_backup/` + recorded video; `make serve` from a previously built `frontend/dist` |
| Frontend fails to build or the API will not start | Recorded video; `make demo` printed scoreboard; `frontend/dist` rebuilt from the lockfile (`npm ci && npm run build`) |
| Node missing on the demo laptop | The CLI, `make demo` and every reported number work without the frontend at all |
| Network down at venue | Demo is fully local; nothing calls the internet (the API serves the SPA from disk, so no CDN, font or map tile is fetched; the map is an offline SVG) |

---

## 22. Performance

Nothing here is a claim; measure on the machine you demo from.

| Item | How to measure |
|---|---|
| `milp` plan on the demo scenario | hard cap `MILP_TIME_LIMIT_S = 30`, incumbent returned. The first plan is published after about 1 to 2 s and better ones follow while HiGHS searches (§16.2): `uv run freshroute run --scenario data/scenarios/practice --policy milp --seed 42` (`solve_seconds` in `run_manifest.json`; the Run button's status `progress.elapsed_s` for each version) |
| Scale | `uv run python -m freshroute.runs.perf --scale 10` (A-40) |
| Replan | residual solve capped at `REPLAN_TIME_LIMIT_S = 2` (A-43): `uv run freshroute replan --run … --event …` |
| MC 200 scenarios (evaluate only) | `uv run freshroute stress --scenario … --n 200`; if too slow, `--n 50` or `--named` |
| `make demo` end to end | time `make demo` |

---

## 23. Decision log

Lives in the repo-root `DECISIONS.md` (D-01 … D-34; D-26 is intentionally unused). Add new decisions there.
