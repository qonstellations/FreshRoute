# DECISIONS.md

Decision log for FreshRoute. `D-xx` = decision (this file); `A-xx` = assumption (`Docs/ARCHITECTURE.md` §20). Add the next free `D-xx` at the bottom; never renumber. If a decision is reversed, mark it **Superseded by D-yy** rather than deleting it.

| ID | Decision | Why | Status |
|---|---|---|---|
| D-01 | Build A+ (A spine + Monte Carlo + replan + newsvendor; narrator stretch) | Highest floor; 70 of 100 rubric points are deterministic metrics | Accepted |
| D-02 | PuLP → HiGHS default; `scipy.optimize.milp` fallback | Readable constraints; both use HiGHS. Confirm at S-04 | Accepted (pending S-04) |
| D-03 | CSV files are the datastore; no DB server | Reproducible, diffable, trivial hidden-scenario loading | Accepted |
| D-04 | Validator re-implements the maths; shares only schema/io | Independence is what makes "0 violations" credible | Accepted |
| D-05 | MILP constraints C4/C5 indexed by arrival day | Demand and receiving capacity bind on arrival, not dispatch | Accepted |
| D-06 | `*_pct` columns hold 0–100 in files and fractions in memory; one conversion in `io.py` | Prevents the classic percent bug | Accepted |
| D-07 | Day-bucket simulator | Matches daily demand tables; simple to test | Accepted |
| D-08 | One shelf price per destination × commodity × day = discount of FEFO-head lot | Matches how a shelf label works; keeps simulator tractable | Accepted |
| D-09 | Template narration first, LLM optional | Explainability points without LLM risk | Accepted |
| D-10 | MILP must beat **FEFO** (not just FIFO) at gate G2 | Avoids the strawman-baseline critique | Accepted |
| D-11 | No statsforecast in the 20 h build | 48 h-plan stretch item; demand quantiles come from p10/p50/p90 columns | Accepted |
| D-12 | 3-person team merges the research doc's 4-role plan: UI + product/pitch + AI = P3 | Team size | Accepted |
| D-13 | 20 h timeline with feature freeze at H17 | Research doc's 24 h plan freezes 3 h before the end; same buffer here | Accepted |
| D-14 | Confirm D-02: PuLP 4.0.0 -> HiGHS (`pulp.HiGHS(timeLimit=, gapRel=)`) is used; `scipy.optimize.milp` (`options` `time_limit`, `mip_rel_gap`) stays the fallback; time-limit and gap options verified | `tests/test_solver_smoke.py`: both APIs give equal objectives on a toy MILP; on a hard 60x5 knapsack a 0.05 s limit returns in ~0.06 s (PuLP status `TimeLimit`, scipy status 1) and a 0.5 gap solves to Optimal. D-02 unchanged. PuLP 4.0 API differs from 3.x: build variables with `prob.add_variable(name, lb, ub, cat=)` (`LpVariable(cat=)` and `LpStatus` are gone); `solve()` returns a stats object, read `.status` against `pulp.LpSolveStatus` | Accepted |

## Open decisions (resolve at H0, `Docs/TODO.md` S-01/S-02)

- Organizer cost model vs ours: which coefficients change?
- Window mode (absolute vs daily), horizon, origin handling cost, hard-violation definition.
- Whether `data/organizer/` may be committed.
- Whether AI coding assistants and external data are permitted by the event rules.

## Default rule: if unspecified, we proceed like this

The open decisions above stay open until the organizers' material answers them (S-01/S-02). **Until then, and for anything the organizers do not specify, the team proceeds with these defaults** and builds so each can be changed in one place (`config.py`, `costmodel.py` or the adapter):

- **Cost model:** our `Docs/ARCHITECTURE.md` §7. The organizers' model overrides it the moment it is known (non-negotiable 1 in `AGENTS.md`).
- **Window mode / epoch:** absolute hours from day 0 at 00:00 (A-01).
- **Horizon end:** unexpired stock is carry-over, valued 0, not spoiled (A-06).
- **Origin handling cost:** 0 (A-07).
- **Hard violations:** the codes in `validator/` as built in F-04.
- **Organizer data:** `data/organizer/` is git-ignored and never committed.
- **AI assistants / external data:** use is allowed (human owner reviews every merge) until the event rules say otherwise; if they forbid it, stop and flag it at the next gate.
- **Anything else:** the module owner decides within 5 minutes, records an `A-xx` or `D-xx`, and moves on.

When an open decision is resolved, add the next free `D-xx` row and update the matching `A-xx`; the default above is then superseded.
