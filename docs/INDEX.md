# FreshRoute documentation index

Start with `00-start-here.md`. The numbered guides explain *why* the system is built the way it is; the reference documents hold the exact formulas and formats.

## Guides (read in order)

There is no `05` guide; the numbering skips it.

| Doc | Read it to understand |
|---|---|
| [00-start-here](00-start-here.md) | The problem, the nine rules, setup and commands |
| [01-the-big-picture](01-the-big-picture.md) | The pipeline from CSV to dashboard |
| [02-cost-model-and-money](02-cost-model-and-money.md) | What net ₹ means and why |
| [03-shelf-life-and-feasibility](03-shelf-life-and-feasibility.md) | Decay, usable life, and the arc pre-filter |
| [04-the-optimizer](04-the-optimizer.md) | The MILP, soft constraints, fallback, scale model |
| [06-simulator-and-baselines](06-simulator-and-baselines.md) | One simulator, the baselines, the ladder |
| [07-validator](07-validator.md) | Why the checker is independent |
| [08-robustness-and-replan](08-robustness-and-replan.md) | Stress, sensitivity, robust plan, profit-vs-spoilage frontier, replan, and the LLM's limits |
| [09-api-and-dashboard](09-api-and-dashboard.md) | The thin API and the UI |
| [10-determinism-and-reproducibility](10-determinism-and-reproducibility.md) | Why reruns match, and where they might not |

## Practical

| Doc | Use it for |
|---|---|
| [SUBMISSION](SUBMISSION.md) | Checklist, deliverables, open questions |
| [DEMO](DEMO.md) | Pitch script and failure playbook |
| [JUDGE-QA](JUDGE-QA.md) | Hard questions with honest answers |
| [GLOSSARY](GLOSSARY.md) | Terms |
| [ORGANIZER-SWAP](ORGANIZER-SWAP.md) | Checklist for adopting an official cost model or data format |

## Reference (source of truth for details)

| Doc | Holds |
|---|---|
| [PS](PS.md) | The problem statement and rubric |
| [ARCHITECTURE](ARCHITECTURE.md) | Behaviour, formulas, config table, assumption log (A-xx) |
| [DATABASE](DATABASE.md) | Table, file and API contracts |
| [../DECISIONS.md](../DECISIONS.md) | Decision log (D-xx) |
| [../AGENTS.md](../AGENTS.md) | Rules and workflow for contributors |

## Which doc answers which question

- "What does this column mean?" → `DATABASE.md`
- "What is the exact formula?" → `ARCHITECTURE.md` §7 to §14
- "Why did we do it this way?" → the guide for that part, then `DECISIONS.md`
- "What did we assume?" → `ARCHITECTURE.md` §20
- "What do I say to a judge?" → `JUDGE-QA.md`
