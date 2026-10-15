# 04 · The optimizer

The allocation brain is a mixed-integer linear program (MILP) solved by HiGHS. This guide explains what it decides, why it is written the way it is, and how it avoids ever failing. Full constraint tables are in `ARCHITECTURE.md` §9.

## What it decides

For every feasible arc (batch, destination, vehicle, day) it picks how many kilograms to ship. It also picks how many trips each vehicle makes to each destination each day, and how much of each batch stays home.

| Variable | Meaning |
|---|---|
| `x` | kg shipped on an arc (continuous) |
| `n` | integer number of trips of a vehicle to a destination on a day |
| `u` | kg left unshipped from a batch |

## The objective in one sentence

Maximize the margin of everything shipped, minus trip costs, minus a penalty for stock that will rot at the origin because we left it there, minus a heavy penalty for using any soft-constraint slack.

A tiny extra term, `ε / usable_life`, breaks ties in favour of shipping the batch with less life left. That is the FEFO (first-expired, first-out) preference, kept deliberately small so it never outweighs real money.

## The constraints that matter

| | Meaning | Why it is shaped this way |
|---|---|---|
| C1 | Shipped plus unshipped equals batch quantity | stock conservation |
| C2 | Load on a trip ≤ vehicle capacity × trips | trucks are finite |
| C3 | Trips per vehicle per day ≤ limit | no teleporting trucks |
| C4 | Receiving capacity per destination per **arrival** day | a dock is full when the truck arrives, not when it left |
| C5 | Shipped ≤ demand × (1 + small slack) per arrival day | do not flood a market that cannot sell it |
| C6 | Every destination gets at least a fraction of the average fill (soft) | stops one market being starved |

C4 and C5 are indexed by arrival day, not dispatch day (D-05). Demand and capacity bind when produce lands, so indexing by departure would let two trucks that leave on different days overload the same morning.

## Why soft constraints and a fallback (Rule 6)

Shipping nothing is always a legal plan, so the hard constraints can never make the model infeasible. Only the fairness rule C6 gets a penalised slack variable. If HiGHS has no incumbent when the 30-second limit ends, the system returns the **FEFO-greedy plan**, flags `fallback_used` in the manifest and shows a banner in the UI. A degraded plan is always better than a crash in front of judges.

## Solver choice (D-02, D-14)

We use PuLP as the modelling layer on top of HiGHS because the constraints read like the maths. `scipy.optimize.milp` (also HiGHS) is the documented fallback if PuLP will not install; no code path uses it today. A smoke test (`tests/test_solver_smoke.py`) proves both APIs give the same optimum and that time-limit and gap options really take effect, because PuLP 4.0 differs from 3.x.

Key settings, all in `config.py`: a 30-second time limit, a 1 % relative gap, and the spoilage weight `LAMBDA_SPOIL = 1`.

## Starting plan and progress

HiGHS spends its first seconds on cutting planes before it finds any plan, and FEFO-greedy is a poor start for this objective (it ignores the fill-balance penalty). So before the search the solver also relaxes the trip integers, solves the LP (about 0.1 s) and rounds the trip counts up by diving; whichever of the two plans scores higher on the objective goes in as the start (usually the rounded LP). That plan and is the first thing the dashboard shows. HiGHS then reports every better plan it finds, and the run publishes each one that scores better in the simulator (see `09`). The fill-balance row is written with one variable per destination instead of a dense row over all arcs; it is the same model, but HiGHS finishes its cut work much sooner (A-51).

## The scale model

On the `practice` scenario and anything larger, the batch-level model has so many variables that HiGHS finds **no** incumbent in 30 seconds (A-50). Above 20,000 candidate arcs (`AGG_ARC_THRESHOLD`) we therefore solve a **pooled** model:

1. Group batches of the same commodity, origin, availability time and a 6-hour life bucket. The group takes the *minimum* life and *maximum* storage temperature of its members, so anything feasible for the group is feasible for every member.
2. Pool vehicles into capacity classes.
3. Solve, then split each arc's kilograms back to the real batches pro rata, re-check feasibility at batch level, drop invalid lines, and hand trips back to real vehicles.
4. Run the independent validator. If any violation remains, fall back to FEFO-greedy on the full scenario.

The honest caveat: on `practice` we cannot compare the pooled solution against an unpooled one, since the unpooled one never finishes. The manifest records how the aggregation went (`solver.aggregation`).

## Why the MILP must beat FEFO (D-10)

FIFO is a strawman, so beating it proves little. The comparison that matters is against FEFO-greedy, a competent heuristic. See `06-simulator-and-baselines.md`.

## Gotchas

- If the time limit stops HiGHS with an incumbent worse than the FEFO-greedy plan, the FEFO-greedy plan is kept instead.
- The 30 s limit is **wall-clock**. On the demo scenario the solver hits that limit, so a different machine, or a busy one, returns a different incumbent. Determinism is exact only for solves that finish early (A-40; see `10`). Intermediate plans shown while it searches differ from run to run for the same reason.
- If you change any objective coefficient, rerun the consistency test between the objective and the simulator (see `02`).
- Replan reuses this same model with frozen shipments subtracted from capacities (see `08`).
