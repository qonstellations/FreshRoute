# 07 · The independent validator

The rubric gives 15 points to allocation feasibility. The validator is how we earn them credibly. Reference: `ARCHITECTURE.md` §11.

## Why it is a separate package (D-04)

If the optimizer and its checker share code, a bug in that code is invisible: the optimizer produces a bad plan and the checker approves it for the same wrong reason. "Zero violations" would then mean nothing.

So `backend/src/validator/` re-implements the feasibility maths from the specification. It may import only the standard library, pandas, numpy, and the two data modules `freshroute.data.schema` and `freshroute.data.io`. It must **not** import `domain/shelflife.py`, `domain/feasibility.py`, `costmodel.py` or anything from the solver.

It sits beside `freshroute` in the same source root only so installed console scripts can import it (D-17). That is packaging, not coupling.

## What it checks

Hard violations (counted as the feasibility score): unknown ids, negative quantity, stock overdraw, shipping before the batch is available, missing lane, mode mismatch, rail slot, shelf life, delivery window, vehicle capacity, trips per day, vehicle availability, receiving capacity, discount over its cap, discount below salvage, and discounts that rise and fall.

That is 16 hard codes (`backend/src/validator/rules.py`). One warning is reported but not counted: `DEMAND_CAP_EXCEEDED` (kilograms over p50 demand plus the overship slack). In a replan, a violation caused only by already-dispatched (frozen) shipments is reported as a `FROZEN_<code>` warning, since it cannot be replanned away. Soft-constraint slack usage and whether the fallback ran are recorded in `run_manifest.json`, not in the validator.

The output is `validation.json` in the run directory.

## How independence is enforced

1. An AST test fails if `validator` imports any other `freshroute` module beyond the two allowed ones.
2. For each violation code, a test injects one known violation into a clean fixture plan and asserts that exactly that code appears.
3. A randomized test checks that the validator's usable-life formula agrees with `shelflife.py`. This is how two copies of one formula stay honest.

## Practical use

- `run`, `replan` and the pooled solver all call it automatically. There is no separate `validate` command.
- `--fail-on-violations` turns the violation count into a non-zero exit code. `make check` uses it on the demo plan.
- The scale model runs the validator before accepting its own answer, and falls back to FEFO-greedy if anything is wrong.

## Gotchas

- If you change the feasibility rules, change them in the validator **and** in `domain/`, then run the agreement test. Do not make one import the other to "avoid duplication"; the duplication is the point.
- The organizers' hard-constraint list, once published, replaces ours. Our violation codes are a best guess until then.
