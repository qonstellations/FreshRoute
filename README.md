# FreshRoute

**Decision support for perishable produce distribution.** Wild Bugs Hackathon 2026.

Every morning a distributor must decide which batch of produce goes to which market, on which truck, on which day, and whether to discount it. Get it wrong and produce rots on the truck while another market runs short. FreshRoute makes those decisions, explains each one, and measures the result against baselines.

> All data in this repository is **synthetic**. All numbers below are **measured** on the `practice` scenario (3-day horizon, seed 42), not projected.

## How it works

1. **Filter.** Drop every shipment whose produce would not have enough shelf life left on arrival, would miss the delivery window, or has no lane.
2. **Optimize.** A mixed-integer program (HiGHS) picks quantities, trips and vehicles for what remains. It never fails: soft constraints, a 30 s limit and a FEFO-greedy fallback. A rounded-LP start puts a first plan on screen in about a second, and better plans stream in while HiGHS keeps searching.
3. **Measure.** One seeded simulator replays every policy's plan, so none can flatter itself.
4. **Audit.** An independent validator, sharing no maths code with the optimizer, checks every hard constraint.
5. **Show.** A FastAPI service and React dashboard display the stored results. They never compute a KPI.

The solver decides, the simulator measures, the validator audits, the UI displays. No LLM makes any decision.

## Results

Synthetic `practice` scenario, seed 42, base realization. Source: `outputs/demo_backup/practice__ladder__s42/`.

| Policy | Spoilage kg | Spoilage % | Demand fulfilled % | Min destination fill % | Net ₹ | Violations |
|---|---|---|---|---|---|---|
| fifo | 937.0 | 1.73 | 77.6 | 34.7 | 318,668 | 19 |
| **fefo** (baseline) | 904.1 | 1.67 | 64.5 | 0.0 | 271,027 | 0 |
| **milp** (FreshRoute) | 854.1 | 1.58 | 83.0 | 52.8 | 442,214 | 0 |
| last_day_50 | 937.0 | 1.73 | 77.6 | 34.7 | 300,674 | 19 |

How to read it honestly:

- **FIFO and `last_day_50` break the rules** (19 violations each). Their higher fulfilment comes from a plan that is not feasible.
- **FEFO is the fair baseline**: it respects shelf life and windows. Against it, FreshRoute adds about **₹171k net** (+63 %) and raises fulfilment from 64.5 % to 83.0 %, mostly by serving more demand at a lower transport bill.
- **Spoilage falls only modestly** (904 → 854 kg). It is not the main driver here.
- **No markdown in FreshRoute's own plan**: a tiered markdown policy gave results identical to `milp` on `practice` and was removed (D-33). `last_day_50` stays as the fair "just discount it" baseline.
- **The MILP is time-limited** (30 s), so its net can differ by a few percent between machines or runs; the figures above are one measured run.

Waterfall, FEFO → FreshRoute: spoilage cost avoided +₹1,357 · extra sales +₹321,101 · extra goods sold −₹186,364 · transport +₹45,543 · handling −₹10,450 · discounts ₹0.

**Robustness** (200 sampled futures, plan evaluated without re-solving, paired against FEFO): net ₹ P10/P50/P90 is 361,681 / 375,373 / 382,259 for FreshRoute against 238,588 / 249,720 / 258,322 for FEFO. FreshRoute wins on net in 100 % of futures and on spoilage in 93.5 %.

Not claimed: replan performance (not yet reviewed enough to quote), and any score against the official rubric.

## Run it

You need [uv](https://docs.astral.sh/uv/) and Node 22+. Python 3.13 is pinned and uv installs it.

```bash
make setup     # install Python and frontend dependencies
make check     # lint, tests, frontend build, validate the demo plan
make demo      # reproduce the table above (ladder + waterfall, seed 42)
make serve     # dashboard + API on http://127.0.0.1:8000
```

No `make` on Windows? Run the recipe lines in the `Makefile` by hand (for example `uv sync`, then `npm ci --prefix frontend`).

Direct commands, all through `uv run`:

```bash
uv run freshroute run --scenario data/scenarios/practice --policy milp --seed 42
uv run freshroute ladder --scenario data/scenarios/practice --seed 42
uv run freshroute stress --scenario data/scenarios/practice --policy milp --n 200 --seed 42
uv run freshroute sensitivity --scenario data/scenarios/practice --seed 42
uv run freshroute replan --run <run dir> --event <event.json>
```

Each run writes `plan.csv`, `trips.csv`, `discounts.csv`, `metrics.json`, `validation.json`, `run_manifest.json`, a dispatch sheet and reason cards to `outputs/<scenario>__<policy>__s<seed>/`. Eleven other synthetic scenarios under `data/scenarios/` (hidden-style, 3× and 10× scale, event and edge cases) exercise odd inputs.

## Design choices worth knowing

| Choice | Why |
|---|---|
| Filter infeasible shipments before the solver | Smaller model, feasibility by construction, and reason cards can say why a market was rejected |
| One simulator for all policies | Fair comparison; policies cannot report their own net |
| Independent validator | "0 violations" means something only if the checker shares no code with the optimizer |
| Compare against FEFO, not only FIFO | Beating a naive baseline proves little |
| Procurement cost inside net ₹ | Otherwise selling more is always profitable |
| Soft constraints plus fallback plan | A degraded plan beats a crash on a hidden scenario |
| CSV on disk, no database | Reproducible, diffable, easy to load hidden scenarios |

## Limits and assumptions

- Data is synthetic. Real Indian post-harvest-loss statistics (NABCONS for MoFPI, 2020–22, 54 commodities) are framing context only, never model inputs.
- No organizer cost model or baseline has been published. Ours is applied identically to every policy and is replaceable in one place; see [`docs/ORGANIZER-SWAP.md`](docs/ORGANIZER-SWAP.md).
- The 30 s solver limit is wall-clock, so on the demo scenario a much slower machine may return a slightly different plan. The model and simulator are deterministic.
- On `practice` and larger, the solver uses a pooled model of similar batches, because the full model finds no solution in 30 s.
- Demand elasticity and the shelf-life decay constant are assumptions; the sensitivity run shows how results depend on them.
- Not built: demand forecasting, live price feeds, vehicle round trips, an organizer-format adapter.

Every assumption is logged in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) §20 and every decision in [`DECISIONS.md`](DECISIONS.md).

## Documentation

Start at [`docs/INDEX.md`](docs/INDEX.md).

| For | Read |
|---|---|
| New developers | [`docs/00-start-here.md`](docs/00-start-here.md), then guides `01`–`10` |
| Judges | [`docs/JUDGE-QA.md`](docs/JUDGE-QA.md), [`docs/DEMO.md`](docs/DEMO.md) |
| Submitting | [`docs/SUBMISSION.md`](docs/SUBMISSION.md) |
| Exact formulas and formats | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md), [`docs/DATABASE.md`](docs/DATABASE.md) |
| Problem statement | [`docs/PS.md`](docs/PS.md) |
| Contributing rules | [`AGENTS.md`](AGENTS.md) |

## Repository map

```
backend/src/freshroute/   data · domain · solvers · policies · engine · runs · generator · api · cli.py
backend/src/validator/    independent constraint checker
backend/tests/            pytest suite and golden hashes
frontend/                 React dashboard
data/scenarios/           synthetic scenarios (CSV)
outputs/demo_backup/      committed reference runs (offline fallback)
docs/                     guides and reference
```
