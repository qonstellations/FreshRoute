# 08 · Robustness, replanning and the role of the LLM

The rubric gives 10 points to robustness and sensitivity. A plan that is optimal for the *forecast* is easy; the question is what happens when the world differs. This guide covers the four tools we use. Reference: `ARCHITECTURE.md` §14.

## Monte Carlo stress test (`runs/stress.py`)

We sample 200 plausible futures (seeded, so repeatable): demand for each destination, commodity and day; travel time for each lane; remaining shelf life for each batch. Samples follow the p10/p50/p90 columns in the data through a piecewise-linear inverse CDF (A-13). Travel time only ever slips later, capped at 1.5 × p90.

Two design choices matter:

- **The plan is evaluated, not re-optimized, in each future.** That is what a real operator lives with: you commit a plan, then reality happens. Re-solving 200 times would measure a different, easier thing.
- **Plan and baseline see the same futures** (common random numbers). The result "plan beats baseline in X % of futures" is then a paired comparison, not luck of the draw.

Output: P10/P50/P90 bands for each KPI plus the share of futures where we win on net ₹ and on spoilage (`stress_summary.json`, `stress.csv`). Fallbacks if time is short: `--n 50`, then `--named` (three fixed scenarios).

## Sensitivity (`runs/sensitivity.py`)

Varies `q10`, elasticity (`ε` against `ε/2`), the overship slack and demand ±20 %, and writes `sensitivity.csv`. It exists to answer the judge question "why should we trust your elasticity?": we do not claim it is right, we show how much the answer depends on it. It takes a few minutes, which is why `make demo` leaves it behind `--with-sensitivity`.

## Event replan (`runs/replan.py`)

Five event types are supported: route delay, capacity drop, demand spike, new order and price shock. An event is a pydantic-validated JSON object (`data/events.py`, `extra="forbid"`), so a typo is rejected, not guessed.

The steps:

1. Apply the event to a copy of the scenario.
2. **Freeze** every shipment that has already left (`dispatch_h ≤ event time`). It cannot be reassigned, though the event may still hurt it in transit.
3. Subtract the frozen use from capacities and demand caps to get a residual problem.
4. Re-solve with a short cap (`REPLAN_TIME_LIMIT_S = 2`), warm-started from the old plan.
5. Write `replan/<event_id>/` with a `diff.json`.

The headline comparison is the honest one: the **old plan executed in the changed world** against the **replanned plan**, not against a world where nothing happened.

Be accurate when describing it. With a 2-second cap on practice-size scenarios, the replan is mostly a repair of the old plan (A-43). The README does not quote a replan figure because the output has not been reviewed enough, so do not quote one either unless you measured it on the day.

## Newsvendor target (`engine/newsvendor.py`)

Instead of planning to median demand, plan to the quantile `c_u / (c_u + c_o)`, where an under-shipped kilogram loses margin and an over-shipped one risks spoilage plus markdown. It is off by default and behind `--newsvendor`; an ablation row in the ladder shows its effect. On the base realization it cannot pay off (A-45), since the base realization is the median.

## The LLM never decides (Rule 5)

Narration is **template-based** and always available: no network, every number is read from the diff or metrics JSON (D-09). There is no LLM code in the repository today. If one is added, it may do exactly two things: turn a sentence into a validated event (failure shows a dropdown instead), and narrate JSON it was given, with a guard that every number in the text must appear in that JSON. HiGHS makes every decision.

This is a deliberate trade. An LLM that chose allocations could not be audited, reproduced or fixed, and the deterministic metrics are 70 of the 100 points.
