# QA.md: judge Q&A answer sheet

Spoken answers (20–30 s each), plus questions our own caveats invite. **Every number here is measured on synthetic data** (practice scenario, seed 42, quiet machine) unless it says otherwise. The source of each number is in brackets; refresh them from `make demo`.

Practice ladder used below [`outputs/practice__ladder__s42/ladder.json`]:

| policy | spoilage kg (%) | fulfillment % | net ₹ | violations |
|---|---|---|---|---|
| fifo | 945.52 (1.70) | 59.59 | 1,271,668 | 37 |
| fefo | 928.33 (1.67) | 54.02 | 1,263,250 | 0 |
| milp | 1,012.72 (1.82) | 62.51 | 1,431,618 | 0 |
| milp_markdown | 1,012.72 (1.82) | 62.51 | 1,431,591 | 0 |

---

## Core Pitch Questions

**1. "Why trust your elasticity?"**
We don't ask you to. Elasticity is a disclosed assumption (A-11): uplift is linear in the discount and capped at 50 % (`MAX_UPLIFT`). On this data it barely matters: markdowns are near-inert and change net by under ₹27 out of ₹1.43 M (A-37). The sensitivity table re-runs at ε and ε/2 (`sensitivity.csv`), demonstrating that net revenue varies by less than 0.2 % even when halving elasticity.

**2. "What if the hidden data is 10× larger?"**
Measured on synthetic data (A-40, A-46): with 2,000 batches and 30 vehicles (10×), the plain model ran far past the 30 s limit. Above a size threshold we now group similar batches and pool identical trucks, solve that smaller model, split it back to real batches and trucks, and re-check it with the independent validator: the plan takes about 11 s (solve ~7 s), solves to optimality, and has 0 violations. With scoped reason cards (A-44), a full run takes ~18 s end-to-end. The demo-size scenario (200 batches) is below the threshold and unchanged. If the solver gives up, we fall back to FEFO-greedy, so we never crash.

**3. "How does this reach a real distributor?"**
As SaaS per hub per month, for distributors, FPO aggregators and cold-storage operators. The output is a dispatch sheet: a priority-ordered CSV plus WhatsApp-style text per truck, which every run already writes (`dispatch_sheet.txt`). The next step is a pilot with one FPO using Agmarknet prices.

**4. "Is your baseline fair?"**
We beat FEFO, not just FIFO. FEFO is the sensible warehouse rule of first-expiry, first-out, already shelf-life-aware. Against FEFO on practice: net ₹1.26 M → ₹1.43 M (+₹168 k), fulfillment 54.0 → 62.5 %. Spoilage is 928 → 1,013 kg: the optimizer fulfills substantially more demand (62.5 % vs 54.0 %), so the 1 % handling loss on those extra delivered kilograms accounts for the minor increase in measured spoilage while netting ₹168 k more economic value. The organizers' official baseline plugs into the same ladder once we have its spec (C-06 / D-25). FIFO is naive by design and shows 37 violations; we show it but don't claim the win against it.

**5. "What does the LLM actually decide?"**
Nothing. HiGHS (an open-source MILP solver) decides. The narration you see is a template over the solver's JSON (`narrator.template_narration`), and a test checks that every number it says appears in that JSON. No network is needed. An LLM may only turn a sentence into a validated event, and the template stays the fallback.

**6. "How do you know the plan is feasible?"**
An independent validator re-implements the rules and imports no optimizer code; a test enforces that. It reports 0 violations for our plans on all validation scenarios. Infeasible routes never enter the model in the first place. The simulator's net ₹ matches the MILP's own objective to the paisa (C-04 consistency test, A-38).

**7. "What if constraints can't all be met?"**
Hard limits stay hard. Fairness across destinations (C6) is soft: slack is penalised and reported in `run_manifest.json`. If there's no solution by the time limit, the FEFO-greedy plan is used and the manifest flags `fallback_used`. That's tested.

**8. "Is this real data?"**
No. It's synthetic and labelled synthetic everywhere. The generator is calibrated per commodity to what NABCONS reports at market stage (A-47): FIFO on practice seed 42 loses tomato 2.65 % (target 3.25), banana 1.84 % (2.40), mango 2.70 % (2.50), potato 0.88 % (0.86), spinach 2.82 % (band 2.3–3.5), 1.70 % overall. Onion is horizon-capped at 0.90 % against a 1.96 % target, because our onions don't expire within 3 days — only the 1 % handling loss bites. Loss statistics are context, not model inputs.

---

## Questions our caveats invite

**9. "Why is markdown barely used?"**
Because the optimizer ships no more than expected demand, so almost nothing is left over to discount. 2 of 507 discount rows are non-zero on practice, shifting net revenue by only ₹26.92 (A-37). Markdown pays off when demand falls short of plan; that's what the stress test probes across 200 sampled futures.

**10. "Your tests have an expected failure. Why?"**
On one generated small scenario, MILP shows 4.29 kg more spoilage than FEFO while earning ₹17.6 k more. That's because it sells onions FEFO left unshipped, and their 1 % handling loss counts as spoilage (A-39). We kept it visible as an `xfail` instead of changing the metric to hide it.

**11. "Do results depend on the machine?"**
For time-limited solves, yes, and we measured it. On a loaded CPU practice MILP gave 1,421 kg / ₹1.58 M, versus 1,013 kg / ₹1.43 M on a quiet machine (A-40). Solves that finish under the limit are bit-identical; a test checks `metrics.json` byte for byte (C-08). The demo runs on a quiet laptop.

**12. "Where does the extra money come from?"**
From the waterfall on practice, FEFO → FreshRoute [`waterfall.json`]: extra sales at list price **+₹168,923**, spoilage cost avoided −₹885, transport +₹9,167 (a saving), handling −₹8,838, discounts −₹27. Net ₹1,263,250 → ₹1,431,591; it reconciles to ±₹0.01 (tested).

**13. "Does the UI work offline?"**
Yes. FastAPI serves the built React app and the outputs from one local origin, with no external calls (D-18, D-20). The route network map is an offline SVG (D-24), fonts are bundled locally via Fontsource, and no external tiles or CDNs are contacted.

**14. "How fast is a replan?"**
Replan re-solve is capped at 2 s (`REPLAN_TIME_LIMIT_S`). Measured on practice seed 42 with 105 of 313 shipments frozen, `replan_run` finishes in 3.1–3.4 s in-process (residual HiGHS solve 2 s, arcs 0.9 s, validation and simulation 0.45 s), or 4.2 s via CLI including interpreter startup (A-43).

