# 00 · Start here

This is the first document to read. It tells you what FreshRoute is for, how the pieces fit together, which rules you must never break, and which commands you will actually type. The numbered guides (`01` to `10`) then take the core parts one at a time. The older reference documents (`ARCHITECTURE.md`, `DATABASE.md`, `DECISIONS.md`) stay the source of truth for exact formulas and file formats; these guides explain the *why*.

## The problem in plain words

A produce distributor holds batches of tomatoes, onions, leafy greens and similar goods. Each batch has a quantity and a **remaining shelf life** that is ticking down, and ticking down faster when the truck is warm. Several markets want the produce, but each has its own demand, price, delivery window and receiving capacity. Trucks are limited, cost money, and take hours to arrive.

Every day the planner has to answer four questions:

1. Which batch should leave first?
2. Which market should it go to?
3. On which vehicle and on which day?
4. Should it be discounted, and by how much?

A bad answer means produce rots on a truck, or a market goes short while another is flooded. The hackathon problem statement (`docs/PS.md`) asks for a decision-support platform that makes these calls, explains them, and **compares the result against a baseline** on spoilage, demand fulfilment and net money.

## What FreshRoute does

FreshRoute reads a scenario (a folder of CSV tables), builds only the shipments that can physically work, asks a mixed-integer solver (HiGHS) for the most profitable plan, and then **replays the plan through one shared simulator** to measure it. A separate, independent validator checks the plan for rule violations. A small API and a React dashboard show the stored results.

The one-line summary of the design is: **the solver decides, the simulator measures, the validator audits, the UI only displays.** Most of the rules below follow from that sentence.

## The system on one page

```
scenario CSVs ─► load + integrity checks ─► feasibility arcs ─► policy (FIFO / FEFO / MILP)
                                                                      │
                                    plan.csv + trips.csv + discounts.csv
                                                                      │
                          ┌───────────────────────┬───────────────────┘
                          ▼                       ▼
                  independent validator      shared simulator ─► metrics.json
                  (validation.json)                                   │
                                                     API serves outputs/ ─► React dashboard
```

Read `01-the-big-picture.md` for the walk-through.

## The nine rules, and why each exists

These are in `AGENTS.md`. They look strict because each one protects a specific thing judges will probe.

| Rule | Why it exists |
|---|---|
| **1. The organizers' cost model and data format override ours.** Coefficients live only in `domain/costmodel.py`, `config.py` or the dataset. | All teams are scored on one cost model. If the organizers publish theirs, we must be able to swap in one place and not hunt through the code. |
| **2. The validator is an independent package.** | "Zero violations" is only believable if the checker does not share code with the thing it is checking. See `07-validator.md`. |
| **3. One simulator scores every policy.** Policies never compute their own net ₹. | Otherwise a policy can flatter itself. Comparing FIFO, FEFO and the MILP is only fair if they are all measured by the same ruler. |
| **4. Everything is deterministic.** Randomness only through `numpy.random.default_rng(seed)`; sort before iterating. | Judges and teammates must be able to rerun and get identical numbers. See `10-determinism-and-reproducibility.md`. |
| **5. The LLM never decides.** HiGHS decides. An LLM may only parse a sentence into a validated event, or narrate JSON it was handed. | An LLM that picks allocations cannot be audited or reproduced. |
| **6. Never crash on a scenario.** Soft constraints, a solve time limit and a greedy fallback. | A hidden scenario may be odd. A degraded plan beats a stack trace in front of judges. |
| **7. Measured numbers only.** Synthetic data is labelled synthetic. Projected scores are never presented as results. | Judges reward honesty, and one inflated claim discredits every other number. |
| **8. The UI shows, the engine decides.** The API and frontend never compute a KPI. | Every number on screen can be traced to a file in `outputs/`. See `09-api-and-dashboard.md`. |
| **9. Add-ons are flags.** Stress, replan and newsvendor can be removed without breaking the core. | The core must stay solid even if an extra is half-finished. |

## Set up and run

You need `uv` (it owns Python), Node 22 or newer, and Python 3.13 (pinned in `.python-version`; uv fetches it).

```bash
make setup                 # uv sync + npm ci --prefix frontend
make check                 # ruff + pytest + frontend build + validate the demo plan
make demo                  # the ladder and waterfall on the practice scenario, seed 42
make serve                 # build the SPA and serve everything on http://127.0.0.1:8000
```

There is no `make` on Windows by default. Either install it (for example ezwinports) or copy the recipe lines from the `Makefile` and run them by hand, for example `uv sync` then `npm ci --prefix frontend`.

Commands you will use most:

```bash
uv run freshroute run --scenario data/scenarios/practice --policy milp --seed 42
uv run freshroute ladder --scenario data/scenarios/practice --seed 42
uv run freshroute stress --scenario data/scenarios/practice --policy milp --n 200 --seed 42
uv run freshroute replan --run <run dir> --event <event.json>
uv run pytest -q
```

Everything is run through `uv run`. Do not use `pip` or add a `requirements.txt` (D-15).

## Where to go next

| You want to… | Read |
|---|---|
| understand the data flow | `01-the-big-picture.md` |
| understand what "net ₹" means | `02-cost-model-and-money.md` |
| change the optimizer | `03` then `04` |
| understand how we are compared to baselines | `06-simulator-and-baselines.md` |
| submit | `SUBMISSION.md` |
| prepare for judges | `JUDGE-QA.md` and `DEMO.md` |
| look up a term | `GLOSSARY.md` |

## Working conventions

- Small commits in the form `type(scope): summary` (types: feat, fix, test, docs, chore, refactor, perf, build). `git pull --ff-only` before pushing.
- Run `make check` before every push.
- A change to a table, JSON file, CLI, API endpoint or public function signature updates its document in the same change. If a data format changed, bump `schema_version`; if an endpoint shape changed, bump `api_version`.
- New assumption: take the next free `A-xx` in `ARCHITECTURE.md` §20. New decision: take the next free `D-xx` in `DECISIONS.md`.
- Never commit `.env`, keys, `.venv`, `node_modules/`, `frontend/dist/`, or `outputs/` (except `outputs/demo_backup/`).
