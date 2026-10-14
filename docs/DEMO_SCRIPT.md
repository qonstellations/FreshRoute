# Demo script — 3:00 pitch (H-05)

All numbers below are **measured on synthetic data** (`data/scenarios/practice`,
seed 42) unless labelled otherwise. Source file for each number is in brackets.
Refresh from `make demo` at V-02; never say a projected number.

Locked demo: `config.DEMO_SCENARIO = data/scenarios/practice`, `DEMO_SEED = 42`.
One URL: `make serve`. Backup: `outputs/demo_backup/` + video. Wi-Fi off.

## 0:00–0:20 Hook (say exactly this)

> "India's government-commissioned NABCONS study found tomatoes lose about
> 8.4 % at the farm stage and a further 3.25 % at the market stage — godowns,
> wholesalers, retailers and transport. Post-harvest loss for tomato overall is
> valued at roughly ₹5,921 crore in that study. The market-stage slice is the
> part a distributor can actually move."

Rules: never "a year" (source gives no year), never attach ₹5,921 cr to the
3.25 % slice alone (it is the all-stage figure), 3.25 % is share of output, not
of loss. [docs/TODO.md §10, PRE-03]

## 0:20–0:35 User and moment

"5 a.m. at a hub; ~200 batches, 8 destinations, 5 trucks; 20 minutes to decide
which batch goes where, when, and at what markdown." Counts are the practice
scenario shape — verify with `batches.csv`/`destinations.csv`/`vehicles.csv`
before saying them.

## 0:35–1:30 Live demo, golden path

1. Load scenario → press **Plan** (practice MILP hits the 30 s time limit;
   say the measured seconds on the day, A-40).
2. Scoreboard [`practice__ladder__s42/ladder.json`, measured 2026-10-14]:
   fifo 945.52 kg / 59.59 % / ₹1,271,668 / 37 violations ·
   fefo 928.33 / 54.02 / ₹1,263,250 / 0 ·
   milp 1,012.72 / 62.51 / ₹1,431,618 / 0 ·
   milp_markdown 1,012.72 / 62.51 / ₹1,431,591 / 0.
   Say: "MILP beats FEFO, not just FIFO — net +₹168 k, fulfillment 54 → 62.5 %."
   fifo's 37 violations are the naive baseline ignoring windows/shelf life (A-31).
3. Click rank-1 reason card [`reason_cards.json`]: "B0181 mango → D4 reefer V3,
   dispatched h53, arrives h66.7, slack 12.4 h, margin ₹79.46/kg, priority #1 —
   runner-up D6 at ₹75.41/kg, kept for lower margin." Use the card's real numbers.
4. Dispatch sheet [`dispatch_sheet.txt`]: "V3 trip T-V3-D4-2-1 departs day 2
   05:00, B0181 mango 471.3 kg (slack 12.4 h) + 5 more lots, arrives day 2 18:42."
5. Discount card: markdown is near-inert on this scenario (₹26.92 below milp,
   A-37) — say so, don't oversell it.

## 1:30–2:05 Robustness

1. Canned disruption: NH-48-style `route_delay` +6 h on lanes into one
   destination. Measured on synthetic practice s42: replan 2.9–3.4 s,
   0 violations, frozen rows unchanged (A-43); on `hidden_ev_delay` s201:
   106 frozen, 0 moved, 0 violations, 2.57 s (H-02 dry run).
   Caveat: with the 2 s replan cap the replan can net less than do-nothing on
   delay/capacity events because the old plan keeps selling lots the validator
   rejects — say the ΔKPIs as shown.
2. Fan chart [`stress_summary.json`, n=200, ~54 s]: "across 200 sampled futures
   we beat fefo on net in 100 % and on spoilage in 70 % of paired futures."
3. Sensitivity [`sensitivity.csv`, U-04]: q10 / ε-vs-ε/2 / overship / demand ±20 %
   — the answer to "why trust your elasticity" (A-11, capped uplift).

## 2:05–2:25 Trust

"Zero violations by the independent validator (it re-implements the maths and
imports no optimizer code); one seeded command `make demo`; assumptions in the
README." 10-seed H-02 sweep: practice `milp_markdown` seeds 1–10, 0 violations,
no crashes. Determinism: same seed ⇒ identical `metrics.json` (C-08; `fefo`
practice re-verified identical H-02). 10× scale: 2,000 batches / 50 vehicles →
plan 17.9 s (solve 9.6 s), optimal, 0 violations via aggregation (H-02).

## 2:25–3:00 Commercial

"SaaS per hub per month for distributors, FPO aggregators, cold-storage
operators. Afresh decides what a store orders. Wasteless decides the shelf
price. Celcius books the reefer. **FreshRoute decides which batch goes where,
when, and at what markdown, at the distributor hub.** Next: pilot with one FPO
using Agmarknet prices."

## Deck draft (7 slides, H-05)

1. Hook (NABCONS numbers above) 2. User/moment 3. Demo scoreboard (ladder table)
4. Waterfall fefo→FreshRoute: baseline ₹1,263,250 − 884.71 (spoilage) + 168,922.98
   (sales) + 9,167.10 (transport) − 8,838.10 (handling) − 26.92 (discounts)
   = ₹1,431,591 [`waterfall.json`, reconciles ±₹0.01] 5. Robustness (fan chart +
   replan diff) 6. Trust (validator 0, seed, assumptions) 7. Commercial +
   pilot. Every slide number from `make demo` output only.

## If it breaks on stage

No live debugging. Switch to the backup video; numbers are still safe:
`make demo` prints the scoreboard in the terminal.
