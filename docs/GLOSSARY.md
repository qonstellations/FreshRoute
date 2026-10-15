# Glossary

Terms you will meet in the code, docs and questions from judges.

| Term | Meaning |
|---|---|
| **Arc** | One candidate shipment: (batch, destination, vehicle, dispatch day). `build_arcs` keeps feasible ones and records the reason for each rejection. |
| **Attribution ladder** | The sequence FIFO → FEFO → MILP, run on one simulator to show where each improvement comes from. |
| **Base realization** | The deterministic world with median (p50) demand, travel time and shelf life. Headline numbers use it. |
| **Carry-over** | Stock still alive when the horizon ends. Not spoiled, not valued, but reported. |
| **COGS** | Cost of goods sold: sold kg × unit procurement cost. |
| **Decay / Q10** | How fast shelf life is used up at a given temperature; each 10 °C rise multiplies the speed by `q10` (default 2, unverified). |
| **Elasticity (ε)** | How much demand rises per unit of discount. A guess, so it is stress-tested. |
| **FEFO** | First-expired, first-out. Ship and sell the earliest-expiring stock first. Our comparison baseline. |
| **FIFO** | First-in, first-out. Ignores shelf life. Our naive baseline. |
| **Fallback plan** | The FEFO-greedy plan used if HiGHS finds no incumbent. Flagged in the manifest. |
| **Frozen shipment** | A shipment already dispatched before a replan event; it cannot be reassigned. |
| **Golden hash** | A stored hash of an output, used by tests to catch accidental changes. |
| **Hard / soft constraint** | A hard constraint can never be broken; a soft one has a penalised slack. |
| **HiGHS** | The open-source MILP solver we use. |
| **Horizon** | The planning period in days (3 on practice). |
| **Ladder / waterfall** | The ladder compares policies; the waterfall splits the ₹ difference between two of them into six steps. |
| **Lot** | A batch after arrival at a destination: `batch@destination@arrival_day`. |
| **Markdown** | A price reduction to clear stock. |
| **MILP** | Mixed-integer linear program. |
| **Net ₹** | Revenue − COGS − transport − handling − spoilage cost. |
| **Overship slack** | Small allowance above forecast demand in constraint C5 (5 %). |
| **p10 / p50 / p90** | The 10th, 50th and 90th percentile columns for demand, travel time and shelf life. |
| **Policy** | Anything that turns a scenario into a plan. |
| **Pooled / scale model** | The grouped MILP used above 20,000 candidate arcs. |
| **Reason card** | The explanation of one shipment or discount. |
| **Realization** | One concrete draw of demand, travel time and shelf life. |
| **RSL** | Remaining shelf life, in hours, at the batch's availability time. |
| **Run manifest** | `run_manifest.json`: everything needed to reproduce a run. |
| **Salvage value** | What a spoiled or heavily discounted kilogram can still recover. Discounts never push price below it. |
| **Scenario** | A folder of CSV tables plus `scenario.json`. |
| **Usable life** | Shelf life left on arrival after waiting, transit and handling. Must be at least the minimum sell window. |
| **Validator** | The independent package that checks plans for hard violations. |
