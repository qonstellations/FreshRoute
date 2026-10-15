# 05 · The markdown (discount) rule

The problem statement asks for discounts "using disclosed assumptions or rules". This guide explains our rule, why it is a rule and not an optimization, and, honestly, where it matters and where it does not. Details: `ARCHITECTURE.md` §10.

## The rule in plain words

After the MILP has decided what goes where, we look at each lot (a batch that arrived at a destination) in earliest-expiry-first order and ask: **how likely is this lot to go unsold before it expires?**

1. Estimate the risk: `1 − min(1, expected demand over the lot's remaining life / stock)`.
2. Map risk to a discount tier: below 0.10 → 0 %, 0.10 to 0.30 → 10 %, 0.30 to 0.50 → 20 %, above 0.50 → 35 %.
3. If 24 hours or less of life remain, bump the tier up one step.
4. Cap it: never above the commodity's `max_discount_pct`, and never so deep that the shelf price drops below the salvage value.
5. **Worth-it test:** keep the discount only if the extra units it is expected to sell bring in more revenue than the price cut gives away. Otherwise try a lower tier, then none.
6. Discounts never go down over time for a lot, since a shelf label does not rise again.

## Why a rule, not a second optimizer

- **Disclosure.** Judges can read five numbered steps. A learned or DP-optimized policy would be harder to explain and is explicitly out of scope.
- **Safety.** Every cap is a hard guard. The validator independently re-checks the caps, salvage floor and monotonicity.
- **Separation.** The MILP does not see future discounts, so a flaw in the markdown rule cannot corrupt the allocation. It is also removable as a flag: policy `milp` is the plan without it, `milp_markdown` is the plan with it.

## One shelf price per day (D-08)

A shop has one label on the shelf. The simulator therefore uses a single price per destination, commodity and day, equal to the discount of the lot at the front of the FEFO queue. Lot-level risk is still shown on reason cards.

## The elasticity assumption

Discounts raise demand by `ε × discount`, capped at +50 % (A-11). Elasticity is a guess, and the sensitivity run compares `ε` with `ε/2` for exactly that reason. See `08`.

## Where it matters, honestly

On the `practice` scenario seed 42, `milp_markdown` and `milp` give **identical** results (A-37). The planner ships at most the median demand, so no lot carries surplus stock that a discount could clear. Markdown earns its keep only when demand falls short of the forecast, which is what the Monte Carlo stress test samples.

Say this plainly to judges. Do not claim markdown contributed to the practice-scenario headline. There is also a known gap: `build_discounts` holds lot stock fixed across days, so it can mark down a lot that already sold out; the simulator ignores such rows.

## Gotchas

- The tier thresholds and the 24 h trigger live in `config.py` (`DISCOUNT_RISK_BREAKS`, `DISCOUNT_TIERS_PCT`, `DISCOUNT_TIME_TRIGGER_H`). Boundary handling at 0.30 and 0.50 is a documented convention (A-22).
- The baseline `last_day_50` is a separate, blunt policy: a flat 50 % cut on the last day. It exists so we compare against a fair "just discount it" strategy.
