# Judge Q&A

Likely questions grouped by the rubric, with honest, short answers. Every figure below is **measured on the synthetic `practice` scenario, seed 42** (copy from the README results table, which is copied from `outputs/demo_backup/`). Say "synthetic" whenever you cite a number. If you are not sure of a number, say it comes from `make demo` and show it.

The pattern for a hard question: answer directly, state the limit, show where it is measured.

## General

**What does it do in one sentence?**
It decides which batch of produce goes to which market, when and on which truck, then proves the result by replaying it in a simulator and checking it with an independent validator.

**Is the data real?**
No. The scenarios are synthetic and labelled so. The Indian loss statistics in the README are framing context from published government sources, never model inputs. We chose synthetic data because the organizers permitted it (D-25).

**Is any LLM involved?**
No LLM decides anything, and there is no LLM code in the repository today. The solver decides; narration is template-based.

## Spoilage reduction (20)

**How much did you reduce spoilage?**
Against FEFO, spoilage fell from 904 kg to 854 kg on practice, roughly 6 %. That is modest and we say so. The larger gains are in fulfilment and net ₹.

**Can you cut spoilage further?**
Yes, at a price, and we show both. `milp_robust` (planned on P10 shelf life, P90 travel) gets 726 kg against 854 kg and beats FEFO on spoilage in 100 % of 200 futures, but nets ₹396,895 against ₹442,214. The frontier run shows the same trade-off point by point. 838 of the 854 kg is handling loss, which grows with kg delivered.

**Why did spoilage % not fall more?**
The MILP ships and sells more, and handling loss scales with delivered kilograms, so percentage can look flat while kilograms fall (A-39). The scenario also has a low base spoilage rate.

**Does FreshRoute use discounts?**
No. We built a tiered markdown rule and measured it: on practice it gave results identical to the plain MILP, because the plan ships at most the median demand and leaves no surplus to clear (A-37), so we removed it (D-33). The `last_day_50` baseline is the discount comparison. Every run also writes a discount check (`discount_advice.json`, shown on the Plan tab): for each market and day with stock left it tests every cut and recommends one only where it pays, otherwise it states why (on practice: elasticity below the break-even, so a cut loses more on stock that sells anyway than it clears).

## Demand fulfilment (15)

**How do you measure it, and can it be gamed?**
`Σ min(sold, undiscounted demand) / Σ undiscounted demand`. Discounts raise sales but not the denominator. We also report the minimum destination fill rate so starving one market shows up.

**Your minimum fill is 52.8 %. Is that fair?**
It is an honest report, up from 0 % under FEFO. A soft balance constraint (C6) pushes toward fairness without making the plan infeasible.

## Net economic outcome (20)

**Is it the same cost model for everyone?**
Ours is our own, applied identically to every policy by one simulator. The organizers' model would override it (Rule 1); the README has a table of every formula that would change.

**Why is procurement cost in net?**
Otherwise selling more is always profitable and net is not a margin a business recognises (D-28).

**Is your baseline fair?**
We compare against FEFO, a competent heuristic, not just FIFO (D-10). We also show `last_day_50`, the obvious "just discount it" alternative. FIFO is naive on purpose and is reported with its 19 violations.

## Allocation feasibility (15)

**Why trust "zero violations"?**
The validator is a separate package that re-implements the maths and imports no optimizer code. Tests inject one violation of each kind and require exactly that code to appear.

**What if the solver cannot find a plan?**
We never return "infeasible". Shipping nothing is always legal, only the fairness rule is soft, and if the 30 s limit passes with no plan we fall back to a FEFO-greedy plan and flag it.

## Robustness and sensitivity (10)

**Why trust your elasticity and Q10?**
We do not claim they are right. The sensitivity run shows how results change with `q10`, elasticity (ε against ε/2), the overship slack, and demand ±20 %.

**What happens when the world differs from the forecast?**
The 200-future Monte Carlo test evaluates the committed plan, without re-solving, on the same futures as the baseline. The plan beats FEFO on net in all 200 futures and on spoilage kg in 84.5 %; the robust variant `milp_robust` beats it on spoilage in 100 % (at lower net).

**Can it replan?**
Yes: five event types, with already-dispatched shipments frozen. Be careful: with a 2 s cap it is mostly a repair of the old plan (A-43), and we have not reviewed replan numbers enough to quote.

## Engineering and reproducibility (10)

**Can I rerun it?**
`make setup && make demo`. Seeds are fixed, dependencies locked, and each run writes a manifest with the git SHA and scenario hash. Golden-hash tests guard it.

**Is it exactly deterministic?**
The model and simulator are. The time-limited MILP incumbent can vary on slower hardware, because the 30 s limit is wall-clock (A-40).

**Why a pooled model above 20,000 arcs?**
The full model finds no incumbent in 30 s on practice-size data. The pooled model groups similar batches conservatively, so any arc feasible for the group is feasible for every member; results are re-checked at batch level and by the validator (A-41, A-50).

## Explainability and commercial relevance (10)

**How is each decision explained?**
Reason cards say why a market was chosen and why the runner-up was not (shelf life, window, capacity, demand cap, lower margin), using rejected-arc data. Discount cards (shown for the `last_day_50` baseline) show risk, tier and the salvage floor.

**Who would pay for this?**
Produce distributors, wholesalers, food-logistics firms, cold-storage operators and agri supply-chain platforms (from `docs/PS.md`). The workflow is a morning dispatch sheet per vehicle plus a replan when something breaks.

**What is missing?**
Demand forecasting, real price feeds, live telemetry, multi-day vehicle round trips (A-08) and an organizer-format adapter. We list these as out of scope rather than imply them.
