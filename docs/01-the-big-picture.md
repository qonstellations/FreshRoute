# 01 · The big picture

This guide follows one run from input files to dashboard, and explains why the pipeline is shaped the way it is. Exact function signatures are in `ARCHITECTURE.md` §6; exact file formats are in `DATABASE.md`.

## The pipeline, step by step

1. **Generate or load a scenario.** A scenario is a folder under `data/scenarios/<name>/` with eight CSV tables (batches, commodities, demand, destinations, lanes, prices, vehicles, events), a `geo.csv`, and a `scenario.json`. `freshroute generate` creates our synthetic ones. `data/io.py::load_scenario` reads them, converts units, and runs integrity checks.
2. **Build feasible arcs.** `domain/feasibility.py::build_arcs` lists every possible *(batch, destination, vehicle, dispatch day)* and keeps only the ones where the produce still has enough shelf life on arrival, arrives inside the delivery window, and has a lane. See `03-shelf-life-and-feasibility.md`.
3. **Run a policy.** A policy turns a scenario into a plan: `plan.csv` (what ships where), `trips.csv`, and `discounts.csv`. The policies are FIFO, FEFO, last-day-50 and MILP. See `04` and `06`.
4. **Validate.** The independent `validator` package re-checks the plan from scratch and writes `validation.json`. See `07-validator.md`.
5. **Simulate.** `engine/simulator.py` replays the plan day by day, selling stock and spoiling what expires, and `engine/metrics.py` turns the ledger into `metrics.json`. See `06`.
6. **Explain.** `engine/reasons.py` and `engine/dispatch_sheet.py` produce reason cards and a per-truck dispatch sheet.
7. **Serve and show.** The FastAPI app reads `outputs/` and the React app renders it. See `09`.

Everything a run produces lands in one directory, `outputs/<scenario>__<policy>__s<seed>/`, together with a `run_manifest.json` that records the seed, git SHA, scenario hash and solver status.

## Why it is shaped this way

### Files on disk, no database (D-03)
CSV files are the datastore. Hidden scenarios arrive as files, diffs are readable in git, and nothing has to be started before a demo. A database would add a moving part with no benefit at this scale. The cost is that each run re-reads its tables, which is cheap here.

### Arcs first, then the solver
The expensive, risky part is the optimizer. By removing impossible shipments *before* the model is built, we get two benefits at once: the model is far smaller, and shelf-life feasibility holds **by construction** because an infeasible shipment has no decision variable. Rejected arcs are kept in the table with a `reject_reason`, which later powers the reason cards ("Delhi was rejected because arrival leaves 9 h of life").

### One simulator, many policies (Rule 3)
The temptation in any optimization project is to report the solver's own objective value as the result. That is unfair, because the objective is a model of the world, not the world. Instead every policy hands over a plan and the *same* simulator plays it out. The simulator knows about spoilage at expiry, handling loss, and demand uplift from discounts, so differences between policies are real differences in outcome.

### The validator sits outside the loop
The simulator executes a plan but deliberately does not enforce capacities or windows. That is the validator's job, and it lives in its own package so a bug in the optimizer's maths cannot hide itself. A deliberately naive policy such as FIFO shows both its violations and its economic damage.

### Imports run one way
`cli → runs → engine / domain / data` (D-31). `cli.py` is argparse only; `runs/` orchestrates; `engine/`, `domain/` and `data/` never import from `runs/`. If you find yourself needing the reverse, the code you want belongs lower down.

### The API is a window, not a brain (Rule 8)
`freshroute/api` serves files verbatim and may *enqueue* a run. It never aggregates or derives a KPI. This is why the dashboard's numbers can always be proven by opening the JSON they came from.

## Code map

| Area | Path | Role |
|---|---|---|
| Data | `backend/src/freshroute/data/` | `schema.py` (column-name constants), `io.py` (load, units, checks), `events.py` (event schema) |
| Domain | `.../domain/` | `costmodel.py`, `shelflife.py`, `feasibility.py`, `discount.py` |
| Solvers | `.../solvers/` | `milp_model.py`, `greedy.py` (FEFO fallback), `aggregate.py` (scale model) |
| Policies | `.../policies/` | `fifo`, `fefo`, `last_day_50`, `milp` |
| Engine | `.../engine/` | `simulator`, `metrics`, `reasons`, `dispatch_sheet`, `newsvendor`, `narrator` |
| Runs | `.../runs/` | `runner`, `ladder`, `stress`, `sensitivity`, `replan`, `naming`, `progress` (show-while-solving), `perf` (timing harness) |
| Generator | `.../generator/` | synthetic scenario builder |
| API | `.../api/` | FastAPI app, job queue |
| Validator | `backend/src/validator/` | independent checker |
| Frontend | `frontend/` | React + Vite SPA: landing page and four-tab dashboard |
| Docs | `docs/` | this folder |

Column names always come from the constants in `data/schema.py`, and units are suffixed on names: `_kg`, `_h`, `_inr`, `_inr_kg`, `_c`, `_pct` (0 to 100 in files) and `_frac` (0 to 1 in memory). The percent-to-fraction conversion happens in exactly one place, `data/io.py` (D-06), because mixing the two is the classic way to be wrong by a factor of 100.
