# FreshRoute: Three Hackathon Concept Variants, a Shared Cost Model, and a Winning Build Plan

**Build Variant A, the solver-first "ShelfSense" engine. After its scoreboard works, add the two cheapest pieces of Variant B: a demand-quantile stress test and a one-click disruption replan. Don't build the full agentic stack.** Spoilage, fulfillment, net economics and feasibility together make up 70 of the 100 rubric points. They are deterministic metrics computed against the organizers' cost model and hidden scenarios. A correct optimizer plus an honest simulator wins those points; agentic polish does not.

## TL;DR
- **Pick A+:** an explainable MILP allocation built on HiGHS, using a pre-filtered shelf-life feasibility check and a disclosed, tiered markdown rule. Measure it against an attribution ladder of baselines (FIFO → FEFO-greedy → MILP → MILP + markdown). Then bolt on a stress test and a replan button. Its expected rubric score is about 80–84 out of 100, with the lowest execution risk of the three variants.
- **The ambitious Variant B (forecasting + an OptiGuide-style LLM copilot) has the highest ceiling, about 85, but a risk-adjusted score of only about 74.** Recent benchmarks show LLM agents still fail most end-to-end operations-research tasks. Use the LLM only as an interface and narrator, never as the formulator.
- **Lock the shared cost model and schema (Section F) in the first two hours.** Write the constraint validator and metrics before the optimizer. Every number in the pitch should come from one reproducible command with a fixed seed.

---

## Key Findings (what the research says, and what it means for you)

**The India context is real and quantifiable. Use it in the first 20 seconds of the pitch.**
- MoFPI commissioned the "Study to determine Post harvest losses of Agri Produces in India" from NABARD Consultancy Services (NABCONS) in 2022, with reference year 2020-22. It covered 54 commodities across 15 agro-climatic zones in 292 districts. The reported losses were 6.02–15.05% for fruits and 4.87–11.61% for vegetables (PIB release, 25 July 2025, a written Rajya Sabha reply by MoS Agriculture Ramnath Thakur). The government attributes these losses "primarily" to "inefficient harvesting, handling, storage, and transportation."\[1\]
- **Crop-level split (PIB release 2151371, 1 August 2025, MoS Food Processing Ravneet Singh, Rajya Sabha):**
  - Tomato: 8.37% at the farm stage + 3.25% at the market stage.\[2\]
  - Banana: 5.17% + 2.40%.\[2\]
  - Onion: 5.31% + 1.96%.\[2\]
  - Guava: 11.59% + 3.46%, the worst among fruits.\[3\]
  - Mango: 6.03% + 2.50%.\[2\]
  - Cabbage: 5.83% + 2.32%.\[2\]
  - Potato: 5.1% + 0.86%.\[2\]
  - The "market level" column covers godowns, wholesalers, retailers, processing units and transport.\[2\] That is the slice a distribution decision tool can actually move.
- **Volume and value:** the same release puts quantities lost at 7.36 million MT for fruits and 11.97 million MT for vegetables.\[2\] A December 2024 Lok Sabha reply (release 2081044, MoS Ravneet Singh Bittu) values the losses at ₹29,545.07 crore for fruits and ₹27,459.08 crore for vegetables. Tomato alone is ₹5,921.15 crore, onion ₹5,156.32 crore and banana ₹5,777.01 crore.\[4\]
  - We read the monetary figures from a verbatim third-party copy of the PIB release, because the pib.gov.in page did not resolve. Re-check it before putting it on a slide.
- **Caveat the problem statement itself flags:** these are government post-harvest loss estimates. They are not batch-level shelf-life data. Use them as context and to sanity-check your synthetic baseline, never as model inputs that you claim are "real."

**Market infrastructure facts for credible positioning:**
- **e-NAM:** 1,656 mandis integrated, with 1.80 crore farmers and 2.72 lakh traders registered as of 28 February 2026, and ₹4.82 lakh crore traded since inception (PIB, 17 March 2026).\[5\] It has grown from 1,389 mandis in 2024.\[6\]
- **Cold storage:** a PIB backgrounder ("From Harvest to Home", 28 September 2025) states that "As of June 30, 2025, India has 8,815 cold storages with a combined capacity of 402.18 lakh metric tonnes" (40.22 million tonnes). The FICCI–Grant Thornton Bharat report "India's Cold Chain Infrastructure: From Storage to a Chain" (reported by Business Standard, 5 October 2026) puts this at about 84% of the 48-million-tonne requirement for 2037-38. It also says roughly three-quarters of that capacity is used for potatoes and that over half sits in Uttar Pradesh and West Bengal. Its pitch-worthy framing is that India has built storage but not a *chain*: first-mile pack-houses, reefers and traceability lag.
  - That framing is exactly the gap a dispatch-decision tool fills.
- **Kisan Rail:** a PIB release (PRID 1883175) quotes Agriculture Minister Narendra Singh Tomar's written Lok Sabha reply: "a total of 2359 trips of Kisan Rail trains have been operated on 167 routes, wherein nearly 7.9 lakh tones of consignments have been transported." Sources disagree on the end date of that period. Railways Minister Ashwini Vaishnaw has been reported giving 31 January 2023, while another report of his Rajya Sabha reply gives 7 August 2020 to 30 June 2022. MoFPI's 50% freight subsidy ended on 31 March 2022 and was not extended.
  - **Implication:** rail is a real but non-default mode. Model it as an optional slower, cheaper lane with fixed departure slots.

**Data you can use to calibrate synthetic data:**
- **Agmarknet daily mandi prices** are published on data.gov.in as "Variety-wise Daily Market Prices Data of Commodity". The catalogue was last updated 10 April 2026.\[7\] Fields are state, district, market, commodity, variety, arrival date, and min/max/modal price in ₹ per quintal.\[8\]
  - Divide by 100 to get ₹/kg.
  - The public sample API key reportedly caps responses at 10 records per request (from a third-party GitHub collector, unverified).\[8\] **Download a CSV snapshot before the hackathon. Do not depend on the live API during the demo.**
- **Shelf-life anchors** (temperate cold-storage references; de-rate them for Indian ambient chains):
  - Spinach: 10–14 days at 0°C (FAO, UMaine).\[9\]\[10\]
  - Firm-ripe tomato: 4–7 days at 13–15°C (FAO).\[9\]
  - Banana: "high" perishability, 2–4 weeks potential (FAO).\[9\]
  - Dry onion: 1–8 months at 0°C (UMaine).\[10\]
  - FAO's perishability classes are useful as commodity tiers: "very high" (<2 weeks: spinach, ripe tomato, leafy greens), "high" (2–4 weeks: banana, mango, guava, cabbage) and low (onion, potato).\[9\]

**The state of the art supports a "solver core + explainable rules + LLM interface" architecture:**
- **Markdowns:** an August 2026 arXiv preprint (Bhatia, Gülpınar, Aydın) finds that "multiple early price reductions with successive price reductions can simultaneously increase revenue and reduce waste." It cites real ladders:\[11\]
  - Hoogvliet/Wasteless starts at 2–5% and rises to 10–15% near expiry.\[11\]
  - Finland's S-market cuts 30% during the day and 60% after 9 pm.\[11\]
  - Robert Sanders (UC San Diego Rady School of Management, *Marketing Science*, 2023) modelled the bread category across 97 Pick 'n Save stores and found that "dynamic pricing reduces waste by 21% while increasing the chain's gross margins and consumer surplus by 3% and 0.3%."
  - **Implication:** a disclosed, multi-step ladder is both defensible and backed by the literature. A single "50% off on the last day" is not.
- **FEFO vs FIFO:** an IOP conference paper (IOP Conf. Ser.: Mater. Sci. Eng. 796 012012) cites a prior simulation study: "In the perishable products scenario, FEFO inventory management reduced waste (expired products) by 50% with respect to FIFO." **Implication:** FEFO-greedy is a strong baseline. Your optimizer must beat FEFO, not just FIFO, or a sharp judge will call the comparison a strawman.
- **LLM + solver:** Microsoft's OptiGuide puts the LLM in front of a combinatorial solver to answer "what-if" questions. It was deployed in Azure's supply chain, and its design "does not require sending proprietary data over to LLMs."\[12\]
  - Benchmarks argue against letting the LLM write the model. OR-LLM-Agent tops out at 82.93% accuracy on textbook problems (BWOR).\[13\]
  - On the 2026 ORAgentBench of realistic end-to-end OR tasks, the best configuration passed only 35.51% of tasks.\[14\]
  - **Implication:** the LLM edits parameters and narrates. HiGHS decides.
- **Tooling:**
  - HiGHS is the default LP/MIP solver in SciPy, with `scipy.optimize.milp` since SciPy 1.9.0. It is also available from PuLP and Pyomo under the MIT license.\[15\]\[16\]
  - Nixtla's statsforecast claims to be "500x faster than Prophet" and offers AutoETS with probabilistic intervals.\[17\] That is a vendor benchmark, but speed is what matters in a 24-hour build.

**Competitive landscape (for the 20-second commercial slide):**
- **Afresh** (US): raised $34M in April 2026. It is live in 12,500+ grocery departments and claims up to 25% shrink reduction (vendor claim).\[18\] It does store and DC ordering for US grocers.
- **Wasteless** (Israel/EU): expiry-anchored shelf markdowns using electronic labels. It reports a 40% waste reduction at Edeka Hamburg (vendor claim).\[19\]
- **Celcius Logistics** (India): a cold-chain marketplace for reefer trucks and cold storage. It raised a ₹250 crore Series B in May 2025, co-led by Eurazeo and Omnivore.\[20\]\[21\]
- **Ninjacart** (India): a B2B farm-to-retailer chain. Inc42 quotes CEO Thirukumaran Nagarajan saying the company "moves over 1400 tonnes of fresh produce per day," working with 25,000 farmers and 70,000 retailers across seven cities. That figure dates from around 2019 (in April 2020 the company said "up to 1,500 tons" daily), so treat it as dated.
- **Positioning:** "Afresh decides what a store orders. Wasteless decides the shelf price. Celcius books the reefer. **FreshRoute decides which batch goes where, when, and at what markdown, at the distributor hub.** That is the unowned decision between mandi/cold store and destination."

---

## A. The Three Variants

### Variant A — "ShelfSense Solver" (conservative, solver-first) ✅ RECOMMENDED CORE

**Core idea:** a deterministic, multi-day MILP that allocates batches to (destination, vehicle, dispatch day). Infeasible shelf-life combinations are removed *before* solving, so the plan can never violate them. A transparent tiered markdown rule runs after allocation, and every decision gets a "reason card."

**Differentiator:** an **attribution ladder** that shows exactly where each rupee of improvement comes from: FIFO → FEFO-greedy → MILP → MILP + markdown. Judges see causality, not a black box.

**Technical approach:**
- **Data model:** the shared schema in Section F.
- **Feasibility pre-filter (the core trick):** for every (batch b, destination d, lane ℓ, dispatch day t), compute
  `usable_life_at_arrival = RSL_b − wait_h(t)·decay(T_store) − travel_h(ℓ)·decay(T_transit) − handling_h(d)`.
  - Create the decision variable only if `usable_life_at_arrival ≥ min_sell_window_h(commodity)` **and** the arrival falls inside d's delivery window.
  - Shelf-life feasibility then holds by construction: infeasible arcs have no variable. The pre-filter also shrinks the model a lot.
- **Allocation MILP** (via `scipy.optimize.milp` or PuLP → HiGHS):
  - **Variables:** `x[b,d,v,t]` kg shipped (continuous); `n[v,d,t]` trips (integer); `u[b]` kg left unshipped.
  - **Objective:** maximize Σ expected sell-through revenue − variable transport − fixed trip cost − handling − λ·expected spoilage cost. Add ε·(1/usable_life) as a FEFO tie-breaker.
  - **Constraints:**
    - stock: Σ x ≤ qty_b
    - vehicle: Σ x ≤ cap_v·n
    - trips per day ≤ max_trips_v
    - receiving capacity: ≤ cap_d per day
    - demand cap: Σ_b x[b,d,·,t] ≤ demand_{d,c,t}·(1 + overship_slack)
    - optional allocation balance: fill_rate_d ≥ φ·average fill rate
  - **Size:** 200 batches × 8 destinations × 3 days × 3 vehicles comes to a few thousand variables after filtering. HiGHS should solve that in seconds (our engineering estimate, not a benchmark; confirm on day 0).
- **Dispatch prioritization:** a priority score = urgency (1/usable life) × value at risk (kg × price). The plan lists dispatches in that order, and each line shows its feasibility slack in hours.
- **Discount rule (disclosed):** see Section F. It uses a tiered ladder driven by an "unsold-risk ratio" with a time trigger, a salvage-value floor and a maximum discount per commodity.
- **Baseline:** use the organizers' documented baseline as the official one. Also implement FIFO-nearest-first and FEFO-greedy internally for the attribution ladder.

**Coverage:** all 5 MVP items. Partial coverage of the optional extensions: replanning (re-solve on edited inputs) and a simple uncertainty stress test.

**24–48h feasibility:**
- **Build for real:** simulator, cost model, validator, MILP, discount rule, scoreboard, reason cards, seeded CLI.
- **Fake or keep simple:** map visuals (static coordinates), live prices (cached Agmarknet CSV), temperature (simulated column).

**Judge-perspective score (event rubric):**

| Criterion (weight) | Score | Rationale |
|---|---|---|
| Spoilage reduction (20) | 16 | The feasibility filter plus FEFO tie-break eliminates "doomed" dispatches. The markdown rule clears the tail. |
| Demand fulfillment (15) | 12 | The objective rewards sell-through. The balance constraint stops one destination being starved. |
| Net economic outcome (20) | 16 | Directly optimizes the organizers' cost terms. |
| Allocation feasibility (15) | 14 | Feasible by construction, plus an independent validator showing 0 violations. |
| Robustness & sensitivity (10) | 6 | Deterministic. Only partly mitigated by the stress test. |
| Engineering & reproducibility (10) | 9 | One command, a seed, unit-tested cost model. |
| Explainability & commercial (10) | 7 | Reason cards and a dispatch sheet. Less "wow." |
| **Total** | **80** | Highest floor, lowest variance. |

**Risks and fallbacks:**
- **MILP infeasibility on a hidden scenario.** Fallback: soft constraints with penalty slacks, so the model never returns "infeasible." Report the slack usage.
- **Solve time on large hidden data.** Fallbacks: a 30-second time limit returning the incumbent, or aggregate batches by commodity × RSL bucket.
- **Organizer cost model differs from yours.** Fallback: isolate the cost model in one module that reads all coefficients from the dataset.

---

### Variant B — "FreshRoute Copilot" (ambitious: forecasting + robust planning + LLM what-if)

**Core idea:** Variant A's solver, plus three additions:
1. Probabilistic demand forecasts for each destination × commodity.
2. A quantile ("newsvendor") demand target per destination, with Monte Carlo evaluation across sampled scenarios.
3. An OptiGuide-pattern copilot that turns "NH-48 is jammed, Pune trucks +6 h" into a structured event, re-solves on a rolling horizon with trucks already dispatched frozen, and narrates the diff.

**Differentiator:** the system adapts live and can say *why the plan changed*. That targets the Robustness (10) and Explainability (10) criteria directly.

**Technical approach:**
- **Forecasting:**
  - statsforecast AutoETS (season_length=7) on synthetic or historical sales, with exogenous event flags handled by a simple multiplier.
  - Output P10/P50/P90.
  - Fallback: seasonal-naive.
- **Robust target (secretly simple):** for each destination × commodity, plan to the demand quantile q* = c_u / (c_u + c_o).
  - c_u is the lost margin per kg short. c_o is the spoilage cost plus the markdown loss per kg left over.
  - This is the classic newsvendor critical ratio. It is one line of code and sounds sophisticated, because it *is* principled.
- **Monte Carlo evaluation:** sample 200 scenarios of demand, travel delay and shelf-life error. Execute the fixed plan in the simulator and report a P10–P90 band for each KPI against the baseline.
- **Replan:** an event JSON (`route_delay`, `capacity_drop`, `demand_spike`, `new_order`, `price_shock`) mutates the inputs. Dispatched shipments are frozen and the solver re-solves the rest. A diff view lists the moved batches, the changed discounts and the ΔKPIs.
- **LLM layer (OptiGuide pattern):**
  - The LLM gets only the event schema and returns validated JSON (function calling).
  - The narrator gets only the metrics and diff JSON, never raw data.
  - If parsing fails, the UI drops back to a dropdown of canned events.

**Coverage:** all MVP items, plus the forecasting, replanning and uncertainty-range extensions. The price-feed integration is optional and cached.

**24–48h feasibility:** realistic in 48 hours with 4 people. In 24 hours it is only realistic if the LLM copilot is cut to canned events.
- **Real:** forecast, quantile targets, Monte Carlo, replan.
- **Fakeable:** the natural-language box (it can map to 5 pre-tested intents).

**Judge-perspective score:**

| Criterion (weight) | Full execution | Risk-adjusted | Rationale |
|---|---|---|---|
| Spoilage (20) | 17 | 15 | Quantile targets cut over-shipping into weak markets. |
| Fulfillment (15) | 13 | 12 | Forecast-aware allocation. |
| Net economic (20) | 17 | 15 | Better under uncertainty, but more moving parts. |
| Feasibility (15) | 13 | 11 | A replan bug can break constraints mid-demo. |
| Robustness (10) | 9 | 8 | Directly addressed with bands and replan. |
| Engineering (10) | 7 | 6 | Stochastic pieces hurt reproducibility unless seeded. |
| Explainability (10) | 9 | 7 | The diff narration is compelling, but LLM output can drift. |
| **Total** | **85** | **~74** | High ceiling, real variance. |

**Risks and fallbacks:**
- **LLM hallucinating parameters.** Fallbacks: schema validation and range checks; on failure, "I couldn't parse that — pick from these."
- **Forecast nonsense on short synthetic history.** Fallback: clamp the forecast to [0.5×, 2×] of the trailing mean.
- **Monte Carlo too slow.** Fallback: evaluate rather than optimize per scenario, and cut to 50 samples.

---

### Variant C — "Markdown Maestro" (discount-optimizer-focused)

**Core idea:** treat discounting as the main lever. Allocation is FEFO-greedy with the same feasibility filter. Each batch at each destination then gets an *optimized markdown schedule* over its remaining life.
- The schedule is a monotone non-decreasing ladder drawn from {0, 5, 10, 20, 30, 40}%.
- It is chosen by small dynamic programming / enumeration to maximize expected revenue minus spoilage under a price-elasticity demand curve.

**Differentiator:** it is the variant most literally aligned with the 2026 markdown literature ("multiple early markdowns") and with what Wasteless sells. It also produces the most visually satisfying "price ladder" demo.

**Technical approach:**
- Demand under discount: `D(d) = D0·(1 + ε·d)`, with commodity elasticity ε disclosed in the assumptions.
- State: (days left, stock). Action: next discount ≥ current. Solve backward over ≤ 7 days with stock discretized into 20 buckets. This runs in milliseconds.

**Coverage:** all MVP items, plus the "optimize discount timing under uncertainty" extension. Weak on replanning.

**Judge-perspective score:**

| Criterion (weight) | Score | Rationale |
|---|---|---|
| Spoilage (20) | 15 | Markdowns clear tails, but poor allocation still ships to the wrong places. |
| Fulfillment (15) | 10 | Greedy allocation leaves demand imbalance. |
| Net economic (20) | 15 | Discount revenue is foregone; elasticity assumptions dominate. |
| Feasibility (15) | 11 | The greedy heuristic can breach capacity unless carefully coded. |
| Robustness (10) | 7 | The DP handles demand uncertainty natively. |
| Engineering (10) | 8 | Simple and deterministic. |
| Explainability (10) | 8 | Price ladders are intuitive. |
| **Total** | **74** | Good story, but it optimizes the smaller lever. |

**Main risk:** judges using the same cost model will see that discounts *reduce* revenue per kg. If your elasticity assumption is generous, the gains look manufactured.
- **Fallback:** run a sensitivity analysis showing the result holds at ε/2.

### Generic-rules lens (innovation / technical / impact / presentation)

The user's general weights are innovation 25–30%, technical execution 25–30%, impact 20–25% and presentation 15–20%. On that lens:
- **B leads on innovation** (about 8/10 vs A's 6/10).
- **A leads on technical execution** (9 vs 7).
- They tie on impact.
- **A+ closes most of the innovation gap.** The replan button and robustness bands are the "novel" moments judges remember.
- **This event publishes its own metric-heavy rubric. Optimize for that rubric, not the generic one.**

---

## B. Recommendation: build "A+"

**Pick A as the spine, then add, in this order and only once each previous step is green:**
1. The Monte Carlo stress test with P10–P90 bands. It costs about 2 hours, reuses the simulator, and is worth +2–3 Robustness points.
2. Event-driven replan with frozen dispatches and a diff view. It costs about 3 hours and is worth +2 Robustness and +1–2 Explainability points.
3. The newsvendor quantile demand target. It costs about 1 hour and adds spoilage and net-revenue points.
4. Only then, the LLM narrator over the diff JSON, with canned-event fallback. It costs about 2 hours, adds +1 Explainability point and is a big "wow."

**Why:**
- The 70 metric points punish infeasibility and bugs far more than they reward sophistication.
- A's floor is the highest, and every B add-on is incremental and independently removable.
- C's optimized-markdown idea is folded in only as the *disclosed tiered rule*. A DP markdown is a stretch goal, not the core.

**Expected A+ score: about 82–84 out of 100.**

---

## C. Team Composition and Time Allocation

**Ideal team of 4:**

| Role | Owns | Must-have skill |
|---|---|---|
| 1. Optimization lead | MILP, feasibility filter, replan | PuLP/SciPy-HiGHS, LP modeling |
| 2. Simulation & metrics engineer | Data generator, cost model, simulator, validator, baselines, seeded CLI, tests | pandas, careful accounting |
| 3. Frontend/dashboard | Streamlit (or Next.js) scoreboard, waterfall, reason cards, replan diff, map | Fast UI, charts |
| 4. Product/pitch + AI | Discount rule spec, assumptions README, LLM narrator, pitch deck, demo script, Q&A prep | Storytelling, prompt/schema design |

With a team of 3, merge roles 3 and 4. With a team of 5, add a forecasting/robustness owner for Variant B items.

**24-hour plan:**

| Hours | Focus | Exit criterion |
|---|---|---|
| 0–2 | Read the rubric and dataset; lock the schema, cost model and discount rule; set up the repo and CLI skeleton | The cost model is signed off in writing |
| 2–6 | Data generator (if needed), simulator, metrics, validator, FIFO + FEFO baselines | `run --baseline` prints the 4 KPIs |
| 6–12 | MILP with feasibility pre-filter; discount rule; plan → simulator | MILP beats FEFO on 3 seeds, 0 violations |
| 12–16 | Dashboard: scoreboard, waterfall, reason cards, dispatch sheet | End-to-end click-through works |
| 16–19 | Stress test (Monte Carlo) and replan button | Bands render; replan in under 5 s |
| 19–21 | Hidden-scenario dry runs: edge cases (zero capacity, all-expired batch, demand spike); **feature freeze at H21** | No crashes on 10 random seeds |
| 21–22 | Record a backup demo video; write the README assumptions | Video saved locally |
| 22–24 | Rehearse the pitch 3× with a timer; prep answers to the 5 likeliest judge questions | Under 3:00, every time |

**48-hour plan:** the same sequence with doubled time. Add the newsvendor quantile, statsforecast, the LLM narrator, and optionally the DP markdown by H36. Freeze at H42. Spend the last 6 hours on polish, the video and rehearsal.

**Rule of thumb:** about 40% of hours on engine, simulation and validation, 25% on UI, 15% on robustness and replan, and 20% on pitch, demo hardening and documentation.

---

## D. Demo Flow and 3-Minute Pitch

**Show baseline vs plan as one scoreboard.** Four KPI tiles show Baseline → FreshRoute with Δ:
- spoilage kg and %
- demand fulfilled %
- net ₹ after all costs
- constraint violations (baseline n vs ours **0**)

Two charts sit below the tiles:
- a **net-revenue waterfall:** baseline → +spoilage avoided → +extra sales → −extra transport → −discounts → plan
- an **attribution ladder bar:** FIFO / FEFO / MILP / MILP + markdown

**Script outline:**
- **0:00–0:20 — Hook.** "India loses ₹5,921 crore of tomatoes a year after harvest, by the government's own NABCONS study. 3.25% of that loss happens at the market stage, after the farm gate.\[2\]\[4\] That's the slice a distributor controls."
- **0:20–0:35 — User and moment.** "It's 5 a.m. at a Nashik hub: 60 batches, 7 destinations, 4 trucks. The manager has 20 minutes to decide."
- **0:35–1:30 — Live demo, golden path.**
  - Load the hidden scenario and press **Plan**. The plan appears in about 3 seconds.
  - The scoreboard lights up.
  - Click one tomato batch to open its reason card: "Sent to Pune, not Delhi: Delhi arrival leaves 9 h of life, below the 24 h sell window; Pune leaves 41 h; margin ₹X/kg."
  - Click the discount card: "20% off from Day 2: unsold-risk 0.38, tier 2; still above salvage floor."
- **1:30–2:05 — Robustness.**
  - Press "NH-48 delay +6 h." The replan finishes in about 2 seconds, and a diff shows 4 batches moved and 1 markdown deepened, with the ΔKPIs.
  - Then show the stress-test fan chart: "Across 200 sampled futures, we beat baseline in X% of them."
- **2:05–2:25 — Trust.** "Zero constraint violations, checked by an independent validator. Every number comes from one seeded command, and every assumption is in the README."
- **2:25–3:00 — Commercial.**
  - "SaaS per hub per month for distributors, FPO aggregators and cold-storage operators."
  - "Afresh does store ordering, Wasteless does shelf prices, Celcius books reefers. FreshRoute owns the hub dispatch decision in between."
  - "Next: pilot with one FPO, using Agmarknet prices."

**Coaching:**
- A JetBrains judging write-up (June 2026) warns: "A strong project with a confusing demo loses to a simpler project that the judges understand." Lablab's guide says the value must be clear within 30 seconds and warns against "over-engineering the AI layer."\[22\]\[23\]
- Run the demo **live from local data**, with the recorded video queued as backup.
- Say the measured numbers. Never say projected ones.

---

## E. "Wow" Features That Are Secretly Simple (with fallbacks)

| Feature | Why it impresses | How it's actually built | Fallback |
|---|---|---|---|
| **Reason cards** ("Why this truck?") | Explainability on demand | Template strings filled from the feasibility slack, margin and rank already computed | Static table of top-3 reasons |
| **Disruption button + diff** | Shows live adaptation | Mutate one lane's travel time, re-solve, set-diff two plans | Precomputed scenario loaded instantly |
| **Shelf-life countdown map** | Visceral urgency | pydeck/Leaflet with batches coloured by hours left | Colour-coded table |
| **Attribution ladder** | Proves causality, kills "strawman baseline" critique | Run 4 policies through the same simulator | Single baseline comparison |
| **Robustness fan chart** | Turns uncertainty into a visual | 200 seeded simulator runs → percentile bands | 3 named scenarios (optimistic / base / stress) |
| **Natural-language what-if** | AI moment | LLM → JSON event (schema-validated) → re-solve → narrate metrics JSON | Dropdown of 5 canned events |
| **WhatsApp-style dispatch sheet / PDF** | Plausible ops workflow (commercial points) | Render the plan as a per-driver text message | CSV download |
| **Agmarknet price ticker** | "Real India data" | Cached data.gov.in CSV, replayed | Static price table |

---

## F. Shared Synthetic Dataset Schema and Economic Cost Model

> **Rule #1:** if the organizers publish a cost model, **theirs overrides this one**. Map every coefficient to their columns. The model below exists so all three variants and every baseline are scored identically, and so you can practise before the data arrives.

**Tables (CSV, all times in hours from planning epoch t=0):**

- `commodities`: commodity, perishability_class (very_high / high / low), base_shelf_life_h, ref_temp_c, q10, min_sell_window_h, handling_loss_pct, unit_cost_inr_kg, disposal_cost_inr_kg, salvage_value_inr_kg, price_elasticity, max_discount_pct
- `batches`: batch_id, commodity, origin_hub, qty_kg, remaining_shelf_life_h (P50), rsl_p10_h, rsl_p90_h, storage_temp_c, quality_grade, available_from_h
- `destinations`: dest_id, name, type (mandi / retail_DC / HoReCa / processor), receive_cap_kg_day, handling_time_h, handling_cost_inr_kg, window_open_h, window_close_h
- `demand`: dest_id, commodity, day, demand_kg_p50, demand_kg_p10, demand_kg_p90, event_flag
- `prices`: dest_id, commodity, day, price_inr_kg (modal), price_min, price_max. Calibrate from Agmarknet modal ₹/quintal ÷ 100.
- `lanes`: origin, dest_id, mode (reefer / ambient / rail), travel_h_p50, travel_h_p90, cost_fixed_inr_trip, cost_var_inr_kg, transit_temp_c, departure_slots (rail only)
- `vehicles`: vehicle_id, origin, mode, capacity_kg, available_from_h, max_trips_day
- `events` (hidden-scenario practice): event_id, type (route_delay / capacity_drop / demand_spike / new_order / price_shock), target, magnitude, at_h

**Calibration suggestions (practice data only):**
- Commodity mix: tomato, spinach/leafy greens, banana, mango, onion, potato. This spans FAO's perishability classes.
- Set base shelf life at ambient: tomato about 4–7 days, spinach about 2–3 days, banana about 5–8 days, onion 30+ days. **These are team assumptions, de-rated from cold-storage references.**
- Tune the FIFO baseline so market-stage spoilage lands near NABCONS's market-stage figures, for example tomato about 3.25% and onion about 1.96%.\[2\] That way your "baseline" is plausible, not a strawman.

**Shelf-life decay (disclosed assumption):**
- `decay(T) = q10^((T − ref_temp)/10)`
- One hour at temperature T consumes `decay(T)` hours of remaining life.
- The default q10 = 2 is a standard modelling convention we did not verify for each commodity; expose it as a slider.

**Feasibility (hard):**
- `usable_life_at_arrival = RSL − wait_h·decay(T_store) − travel_h·decay(T_transit) − handling_h ≥ min_sell_window_h`
- The arrival must fall within [window_open, window_close].
- Stock, vehicle capacity, trips per day and receiving capacity must all hold.

**Sales and spoilage simulation (per destination × commodity × day):**
- `effective_demand = demand × (1 + ε × discount)`, capped at demand × (1 + max uplift)
- `sold = min(on_hand_sellable, effective_demand)`, allocated FEFO within the destination
- **Spoiled kg** = transit/handling loss (`handling_loss_pct × delivered`) + delivered-but-unsold at expiry + undispatched stock past expiry at origin

**Economics:**
- **Revenue** = Σ sold × price × (1 − discount)
- **Transport cost** = Σ trips × cost_fixed + Σ kg × cost_var
- **Handling cost** = Σ kg_delivered × handling_cost_inr_kg (origin + destination)
- **Discount cost** (reported separately; already netted inside Revenue, so it is *not* subtracted again) = Σ sold × price × discount
- **Spoilage cost** = Σ spoiled_kg × (unit_cost + disposal_cost − salvage_value)
- **Net economic outcome** = Revenue − Transport − Handling − Spoilage cost
- **Demand fulfillment** = Σ min(delivered_sellable, demand) / Σ demand. Also report the minimum destination fill rate (allocation balance).
- **Feasibility score** = number of violations found by the **independent** validator, which never imports optimizer code.

**Disclosed discount rule (shared by all variants; C replaces it with DP):**
1. For each batch at its destination, compute `risk = 1 − min(1, expected_demand_over_remaining_life / stock)`.
2. Assign a tier:
   - risk < 0.10 → 0%
   - 0.10–0.30 → 10%
   - 0.30–0.50 → 20%
   - > 0.50 → 35%
3. Time trigger: if remaining life ≤ 24 h, step up one tier.
4. Constraints:
   - Discounts are monotone non-decreasing over time.
   - The discount is ≤ max_discount_pct.
   - The discounted price must be ≥ salvage_value.
   - Apply only if the expected Δrevenue from extra units sold > the revenue foregone on units that would have sold anyway.
5. This early, multi-step shape follows the Hoogvliet/Wasteless and S-market ladders documented in the 2026 markdown literature.\[11\]

**Baseline (shared):** the organizers' documented baseline. Internally, also run:
- **FIFO-nearest:** dispatch in arrival order to the closest destination with demand.
- **FEFO-greedy:** dispatch earliest-expiry first to the highest-margin feasible destination.\[24\]
- **Last-day 50% markdown:** the naive industry practice.

---

## G. Prioritized Next-Action Checklist

1. **(Before the event)** Download an Agmarknet CSV snapshot for tomato, onion, banana, potato and spinach for 2–3 representative mandis. Pre-install `scipy>=1.9`, `pulp`, `highspy`, `statsforecast`, `streamlit` and `pydeck`.
2. **(H0)** Read the organizers' baseline and cost model line by line. Write the mapping to Section F in the README.
3. **(H0–2)** Build the independent validator and metrics module first, with unit tests on a hand-computed 3-batch example.
4. **(H2–6)** Build the simulator and the FIFO + FEFO baselines, plus the seeded CLI: `freshroute run --scenario X --policy milp --seed 42 → metrics.json`.
5. **(H6–12)** Build the MILP with the feasibility pre-filter and soft-constraint slacks. Add a 30-second time limit returning the incumbent.
6. **(H8–12)** Add the discount rule and the reason-card fields emitted by the solver pipeline.
7. **(H12–16)** Build the scoreboard, waterfall, attribution ladder and dispatch sheet.
8. **(H16–19)** Add the stress-test bands and the replan button with the diff view.
9. **(H19–21)** Run edge-case scenarios and feature-freeze.
10. **(H21+)** Record the backup video, rehearse 3×, and prep Q&A. Likely questions:
    - "Why trust your elasticity?"
    - "What if the hidden data is 10× larger?"
    - "How does this reach a real distributor?"
    - "Is your baseline fair?"
    - "What does the LLM actually decide?" (Answer: nothing — it translates and narrates.)
11. **(Stretch, 48h only)** Newsvendor quantile targets → statsforecast → LLM narrator → DP markdown.

---

## H. Source Notes and Unverified Claims

- **Verified against official PIB text:**
  - The study scope (54 commodities, 15 agro-climatic zones, 292 districts, reference 2020-22).\[1\]
  - The category loss ranges.
  - The crop-wise farm/market percentages and the million-MT quantities.\[2\]
  - e-NAM's March 2026 figures.\[5\]
- **Secondhand:**
  - The ₹ crore monetary-loss figures (release 2081044) come from a verbatim third-party copy, because the PIB page did not resolve.
  - Tomato's two components sum to 11.62%, versus the official 11.61% upper bound.\[3\] That is likely rounding.
- **Conflicting dates:** the Kisan Rail totals (2,359 trips, about 7.9 lakh tonnes) are reported for periods ending 30 June 2022 in one account and 31 January 2023 in another.
- **Vendor or self-reported claims, unaudited:**
  - Afresh's 25% shrink reduction.
  - Wasteless's 40% waste reduction.
  - statsforecast's "500x faster than Prophet."
  - Ninjacart's 1,400 t/day (quoted by its CEO to Inc42), a figure from around 2019 and now dated.
- **Preprints and secondary sources:**
  - The 2026 markdown study (arXiv 2608.23046) is a preprint.
  - The FEFO "50% less waste" figure is a simulation result cited secondhand in IOP Conf. Ser.: Mater. Sci. Eng. 796 012012.
  - The Agmarknet sample-key 10-record limit comes from a third-party GitHub repository.
- **Temperate reference values:** the shelf-life values come from temperate cold-storage references (FAO, UMaine). The ambient de-rated values and q10 = 2 are **team assumptions** and must be disclosed as such.
- **Not researched in this pass:** OR-Tools routing performance. The recommendation uses HiGHS via SciPy/PuLP, whose integration *is* documented.
- **Our own estimates, not benchmarks:** all rubric scores in this report are judgement-based projections. Solve-time estimates are engineering estimates; verify both against the actual dataset on day 0.

## Sources

1. [SCHEMES TO MINIMISE POST-HARVEST LOSSES](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2148529&reg=48&lang=2)
2. [NABCONS Study Assesses Post-Harvest Losses Across 54 Crops During 2020–22](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2151371&reg=3&lang=2)
3. [India’s Highest Post-Harvest Losses: Guava and Tomato Among the Worst Hit](https://www.global-agriculture.com/india-region/indias-highest-post-harvest-losses-guava-and-tomato-among-the-worst-hit/)
4. <https://www.gleaf.in/uploads//press_release/e92b0779e9f02236f50ca62da4436be2.pdf>
5. [e-NAM Integrates 1,656 Mandis, Benefits Over 1.80 Crore Farmers with ₹4.82 Lakh Crore Trade Since Inception](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2241414&reg=3&lang=2)
6. [\_\_\_\_\_\_\_\_ \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_ National Agriculture Market (e -NAM)](https://static.pib.gov.in/WriteReadData/specificdocs/documents/2026/apr/doc2026413845801.pdf)
7. [Variety-wise Daily Market Prices Data of Commodity](https://www.data.gov.in/resource/variety-wise-daily-market-prices-data-commodity)
8. [GitHub - herrrickshaw/agri-commodity-tracker: Daily India APMC mandi commodity prices (Agmarknet/data.gov.in) + World Bank agriculture panel — fully open sources](https://github.com/herrrickshaw/agri-commodity-tracker)
9. [Section 7: Storage of horticultural crops](https://www.fao.org/4/x5403e/x5403e09.htm)
10. [Bulletin #4135, Storage Conditions: Fruits and Vegetables - Cooperative Extension Publications - University of Maine Cooperative Extension](https://extension.umaine.edu/publications/4135e/)
11. [Dynamic Markdown Strategies for Perishable Products: Waste Reduction versus Profitability](https://arxiv.org/html/2608.23046v1)
12. [Large Language Models for Supply Chain Optimization - Microsoft Research](https://www.microsoft.com/en-us/research/publication/large-language-models-for-supply-chain-optimization/)
13. [OR-LLM-Agent: Automating Modeling and Solving of Operations Research Optimization Problems with Reasoning LLM](https://arxiv.org/html/2503.10009v2)
14. [ORAgentBench: Can LLM Agents Solve Challenging Operations Research Tasks End to End?](https://www.alphaxiv.org/abs/2606.19787)
15. [Software](https://www.maths.ed.ac.uk/school-of-mathematics/research/data-decisions/optimization-and-operational-research/software)
16. [HiGHS optimization solver](https://en.wikipedia.org/wiki/HiGHS_optimization_solver)
17. [Statistical ⚡️ Forecast - Nixtla](https://nixtlaverse.nixtla.io/statsforecast/index.html)
18. [Afresh Raises \$34M to Scale AI Across the Grocery Industry - Perishable News](https://perishablenews.com/retailfoodservice/afresh-raises-34m-to-scale-ai-across-the-grocery-industry/)
19. [Wasteless - Solar Impulse Efficient Solution](https://impulse-foundation.com/solutions/solutions-explorer/portfolio/solutions/wasteless)
20. [How Swarup Bose Built Celcius Into India's Largest Cold Chain Platform in Five Years](https://www.founderthesis.com/p/how-swarup-bose-built-celcius-into)
21. [Founded Year](https://www.cbinsights.com/company/celcius)
22. [How to Win a Hackathon: Notes From the Judging Table - The JetBrains Blog](https://blog.jetbrains.com/ai/2026/06/how-to-win-a-hackathon-notes-from-the-judging-table/)
23. [How to Win an AI Hackathon](https://lablab.ai/guide/how-to-win-an-ai-hackathon)
24. [FIFO vs FEFO for Food Distributors](https://bmobileroute.com/blogs/fifo-vs-fefo-inventory-method-food-distributors)
