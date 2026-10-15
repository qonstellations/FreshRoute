# 06 · The simulator, the baselines and the ladder

Judges score us by comparing outcomes against a baseline. This guide explains how we make that comparison trustworthy. Reference: `ARCHITECTURE.md` §12 and §13.

## One simulator scores everyone (Rule 3)

`engine/simulator.py` is the only place outcomes are computed. A policy hands over `plan.csv` and `discounts.csv`; the simulator replays them day by day:

1. Shipments arrive. A small handling loss is taken off immediately.
2. The shelf discount for the day is set from the lot at the front of the queue.
3. Customers buy, earliest-expiry lots first, up to the (possibly discount-boosted) demand.
4. Lots that expire overnight are written off as spoiled.
5. Stock left at origin is spoiled if it expires inside the horizon, otherwise reported as carry-over.

It is a **day-bucket** model (D-07) because demand is given per day; anything finer would add complexity with no data to back it.

The simulator does **not** enforce capacities or delivery windows. That is the validator's job (see `07`). The consequence is useful: a bad plan reveals both its violations and its economic damage.

Policies never report their own net ₹. They cannot flatter themselves.

## The policies

| Policy | What it does | Why it is in the set |
|---|---|---|
| `fifo` | Send in arrival order to the nearest market with demand. Ignores shelf life and windows. | What a naive dispatcher does. Its violations are reported honestly. |
| `fefo` | Earliest-expiry batch first, to the best-margin **feasible** arc, same demand caps as the MILP. | The real baseline. Beating FIFO alone would be a strawman (D-10). |
| `last_day_50` | FIFO plus a 50 % markdown once a lot has 24 h of life or less left (capped at the salvage floor). | A fair "just discount it" comparison. A likely judge question. |
| `milp` | HiGHS allocation, no markdown. | This is "FreshRoute" (D-33). |
| `organizer_baseline` | Recognised but refuses to run. | No organizer material exists yet (D-25). |

`FEFO` is the comparison baseline in `config.py` (`BASELINE`). If the organizers publish a baseline, implement it exactly from their document and switch `BASELINE`.

## The attribution ladder

`freshroute ladder` runs `fifo → fefo → milp` (plus `last_day_50` as an extra) on the same scenario, seed and simulator. It answers "where did each rupee of improvement come from?" step by step, instead of one before/after number. Headline results use the deterministic base realization (median demand, median travel, median shelf life).

## The waterfall

From the FEFO net to the FreshRoute net, in six steps: spoilage cost avoided, extra sales, cost of the extra goods sold, extra transport, extra handling, discounts given. A unit test asserts that `baseline net + Σ steps = plan net` to within ₹0.01. If the bars do not add up, something is being counted twice.

## How to read the practice results

Measured on the synthetic `practice` scenario, seed 42, from `outputs/demo_backup/`:

- FIFO and `last_day_50` show 19 violations each; their higher fill rate comes from an infeasible plan.
- Against FEFO, the MILP adds about ₹171k net. The gain comes mainly from **fulfilling more demand** at a lower transport bill, not from a large drop in spoilage (904 kg to 854 kg).
- Spoilage % can rise for a plan that ships more, because handling loss scales with delivered kilograms (A-39).

Always quote numbers with their scenario and seed, and always say synthetic. The README holds the current table; copy from there, never from memory.

## Gotchas

- Do not add a "quick" metric inside a policy. Anything reported must come from `engine/metrics.py`.
- Numbers drift when the generator or cost model changes. `make demo` is the single command every reported figure must come from.
