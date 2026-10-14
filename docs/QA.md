# QA.md: judge Q&A answer sheet

Spoken answers (20–30 s each) for TODO §11, plus questions our own caveats invite. **Every number here is measured on synthetic data** (practice scenario, seed 42, quiet machine, 2026-10-14) unless it says otherwise. The source of each number is in brackets; refresh them from `make demo` at V-02. `[pending X]` = not measured yet, so don't say a number.

Practice ladder used below [`outputs/practice__ladder__s42/ladder.json`; TODO §5 G2 result]:

| policy | spoilage kg (%) | fulfillment % | net ₹ | violations |
|---|---|---|---|---|
| fifo | 1,786 (3.31) | 67.1 | 1,358,103 | 14 |
| fefo | 1,342 (2.49) | 66.2 | 1,413,264 | 0 |
| milp | 1,244 (2.31) | 79.3 | 1,655,781 | 0 |
| milp_markdown | 1,244 (2.31) | 79.3 | 1,655,293 | 0 |

---

## TODO §11 questions

**1. "Why trust your elasticity?"**
We don't ask you to. Elasticity is a disclosed assumption (A-11): uplift is linear in the discount and capped at 50 % (`MAX_UPLIFT`). On this data it barely matters: markdowns are near-inert and change net by under ₹500 out of ₹1.66 M (A-37). The sensitivity table re-runs at ε and ε/2 [pending U-04: say the result only once `sensitivity.csv` exists].

**2. "What if the hidden data is 10× larger?"**
Measured on synthetic data (A-40, A-46): with 2,000 batches and 30 vehicles (10×), the plain model ran far past the 30 s limit. Above a size threshold we now group similar batches and pool identical trucks, solve that smaller model, split it back to real batches and trucks, and re-check it with the independent validator: the plan takes about 11 s, solves to optimality, and has 0 violations. Honest caveat: building the full route table for the reason cards still takes about 50 s at that size, so a full run is about 60 s. The demo-size scenario (200 batches) is below the threshold and unchanged. If the solver gives up, we fall back to FEFO-greedy, so we never crash.

**3. "How does this reach a real distributor?"**
As SaaS per hub per month, for distributors, FPO aggregators and cold-storage operators. The output is a dispatch sheet: a priority-ordered CSV plus WhatsApp-style text per truck, which every run already writes (`dispatch_sheet.txt`). The next step is a pilot with one FPO using Agmarknet prices.

**4. "Is your baseline fair?"**
We beat FEFO, not just FIFO. FEFO is the sensible warehouse rule of first-expiry, first-out, already shelf-life-aware. Against FEFO on practice: spoilage 1,342 → 1,244 kg, net ₹1.41 M → ₹1.66 M, fulfillment 66.2 → 79.3 %. Same on 3 more generated seeds (TODO §5 G2 result). The organizers' official baseline plugs into the same ladder once we have its spec (C-06). FIFO is naive by design and shows 14 violations; we show it but don't claim the win against it.

**5. "What does the LLM actually decide?"**
Nothing. HiGHS (an open-source MILP solver) decides. The narration you see is a template over the solver's JSON (`narrator.template_narration`), and a test checks that every number it says appears in that JSON. No network is needed. [If AD-09 lands: an LLM may only turn a sentence into a validated event, and the template stays the fallback.]

**6. "How do you know the plan is feasible?"**
An independent validator re-implements the rules and imports no optimizer code; a test enforces that. It reports 0 violations for our plans on all 4 G2 scenarios. Infeasible routes never enter the model in the first place. The simulator's net ₹ matches the MILP's own objective to the paisa (C-04 consistency test, A-38).

**7. "What if constraints can't all be met?"**
Hard limits stay hard. Fairness across destinations (C6) is soft: slack is penalised and reported in `run_manifest.json`. If there's no solution by the time limit, the FEFO-greedy plan is used and the manifest flags `fallback_used`. That's tested.

**8. "Is this real data?"**
No. It's synthetic and labelled synthetic everywhere. The generator is calibrated so the naive-FIFO baseline loses about what NABCONS reports at market stage: tomato 3.25 %, our FIFO about 3.3 % overall on practice. Onion is capped at 0.82 % against a 1.96 % target, because our onions don't expire within 3 days (A-21/A-30). Loss statistics are context, not model inputs.

---

## Questions our caveats invite

**9. "Why is markdown barely used?"**
Because the optimizer ships no more than expected demand, so almost nothing is left over to discount. 1 of 551 discount rows is non-zero on practice (A-37). Markdown pays off when demand falls short of plan; that's what the stress test probes [pending AD-03].

**10. "Your tests have an expected failure. Why?"**
On one generated small scenario, MILP shows 4.29 kg more spoilage than FEFO while earning ₹17.6 k more. That's because it sells onions FEFO left unshipped, and their 1 % handling loss counts as spoilage (A-39). We kept it visible as an `xfail` instead of changing the metric to hide it.

**11. "Do results depend on the machine?"**
For time-limited solves, yes, and we measured it. On a loaded CPU practice MILP gave 1,421 kg / ₹1.58 M, versus 1,244 kg / ₹1.66 M on a quiet machine (A-40). Solves that finish under the limit are bit-identical; a test checks `metrics.json` byte for byte (C-08). The fix in hand is a work limit instead of wall time (H-02). The demo runs on a quiet laptop.

**12. "Where does the extra money come from?"**
From the waterfall on practice, FEFO → FreshRoute [`waterfall.json`]: extra sales at list price **+₹246,772**, spoilage cost avoided +₹2,214, transport −₹9,156 (a saving), handling ₹15,630 more, discounts ₹483. Net ₹1,413,264 → ₹1,655,293; it reconciles to ±₹0.01 (tested).

**13. "Does the UI work offline?"**
Design says yes: FastAPI serves the built React app and the outputs from one local origin, with no external calls (D-18, D-20). [pending R-02: say "yes" only after the Wi-Fi-off test passes on the demo laptop.]

**14. "How fast is a replan?"**
[pending AD-02: quote only the measured `solve_seconds`.]
