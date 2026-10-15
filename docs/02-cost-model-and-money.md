# 02 · The cost model: what "net ₹" means

Everything the system optimizes, simulates and reports is measured in rupees through one cost model. This guide explains it and, more importantly, why it is built the way it is. The formulas are in `ARCHITECTURE.md` §7.

## The rule that governs everything

**If the organizers publish a cost model, theirs overrides ours (Rule 1).** Our coefficients exist so that all policies are scored identically and so we can practise before real data arrives. Therefore:

- Every formula lives in exactly one file, `domain/costmodel.py`.
- Every parameter value lives in `config.py` or in the dataset itself.
- No cost literal may appear anywhere else, including tests of other modules and the frontend.

The README has a "cost-model comparison" table listing each formula that would have to change if the organizers' model differs. It is the checklist for the day their material appears.

## The definition

```
Net = Revenue − COGS − Transport − Handling − Spoilage cost

Revenue       = Σ sold × price × (1 − discount)
COGS          = Σ sold × unit_cost
Transport     = Σ trips × fixed_cost_per_trip + Σ kg × variable_cost_per_kg
Handling      = Σ kg delivered × handling_cost_per_kg
Spoilage cost = Σ spoiled_kg × (unit_cost + disposal_cost − salvage_value)
```

The **discount cost** is reported separately for the waterfall, but it is *already inside Revenue* because revenue is computed at the discounted price. It is never subtracted a second time.

## Why procurement cost is in net (D-28)

An early version had no cost of goods sold. The result was that selling more was always profitable, because every kilogram sold was pure revenue, and "net" was not a margin any business would recognise. A judge asking "would a distributor actually run this plan?" would have found the flaw immediately.

So stock is treated as bought at `unit_cost`. A sold kilogram carries that cost as COGS. A spoiled kilogram carries it inside the spoilage cost. Stock still alive when the horizon ends is inventory held at cost: it carries neither COGS nor spoilage and is reported as `carryover_kg` so nothing is hidden (A-06).

This is a modelling choice, not a fact from the problem statement. If the organizers' dataset has no procurement cost, the `unit_cost` column becomes zero and the formulas still work.

## Why spoilage cost looks the way it does

A spoiled kilogram loses the money we paid for it, costs extra to dispose of, and recovers only whatever salvage value remains. That gives `unit_cost + disposal_cost − salvage_value`. Spoilage is therefore not a flat penalty; cheap, salvageable produce hurts less than expensive produce that must be binned.

## Other numbers judges ask about

- **Demand fulfilment** is `Σ min(sold, base_demand) / Σ base_demand`, where `base_demand` is the *undiscounted* demand. Discounts can raise sales but cannot inflate the denominator, so fulfilment cannot be gamed by markdowns.
- **Minimum destination fill rate** is reported next to it. It exposes plans that feed three markets well and starve a fourth.
- **Spoilage %** is `spoiled_kg / total batch kg × 100`. It is measured within the horizon.
- **Feasibility** is the number of hard violations reported by the validator, never by the optimizer.

## Where the optimizer meets the cost model

The MILP objective uses a *per shipped kilogram margin* derived from the same formulas (`costmodel.shipped_margin`). A consistency test checks that, with slack off and markdown off, the simulator's net for a MILP plan equals the MILP's own objective within tolerance. If you change a cost formula and that test fails, the model and the simulator have drifted apart.

## Gotchas

- Use `FLOAT_TOL` from `config.py` for comparisons, never `==` on floats.
- Percent columns are 0 to 100 on disk and fractions in memory; convert only in `data/io.py`.
- Demand uplift from a discount is `1 + min(ε × discount, 0.5)`. The 0.5 cap (A-11) stops an elasticity guess from creating unlimited demand.
