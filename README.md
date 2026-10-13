# FreshRoute

**Wild Bugs Hackathon 2026** · team of 3 · 20-hour build

FreshRoute is a hub-level decision tool for perishable produce. Given batches with remaining shelf life, destinations with demand and delivery windows, and vehicles with capacities, it decides **which batch goes where, when, and at what markdown**.

- **Spine:** shelf-life feasibility pre-filter → allocation MILP (HiGHS) → disclosed tiered markdown rule, scored by one seeded simulator and checked by an independent validator.
- **A+ add-ons (each behind a flag):** Monte Carlo stress test with P10–P90 bands, event-driven replan with a diff view, newsvendor demand target. An LLM narrator is stretch only; it never decides.

> **Status:** planning/documentation phase. No code yet; the sections marked *TBD* are filled by the tasks named next to them.
> **Data:** practice scenarios are **synthetic** and always labelled so. Real-world loss statistics are context, not model inputs.

## Documentation

| Doc | Purpose |
|---|---|
| [`Docs/ARCHITECTURE.md`](Docs/ARCHITECTURE.md) | How the system works: cost model, MILP, markdown, simulator, add-ons, assumption log |
| [`Docs/DATABASE.md`](Docs/DATABASE.md) | Data contracts: input tables, output files, event schema, organizer mapping |
| [`Docs/TODO.md`](Docs/TODO.md) | Schedule, tasks, gates, cut list, pitch and Q&A prep |
| [`Docs/CONTRIBUTING.md`](Docs/CONTRIBUTING.md) | Team workflow, git rules, code standards, testing |
| [`DECISIONS.md`](DECISIONS.md) | Decision log (`D-xx`) |
| [`AGENTS.md`](AGENTS.md) | Instructions for AI coding assistants working in this repo |
| [`Docs/RESEARCH-v1.md`](Docs/RESEARCH-v1.md) | Background research and variant comparison (some figures secondhand; see its §H) |

**Rule #1:** if the organizers publish a cost model or dataset format, theirs overrides everything in these docs.

## Quickstart *(TBD — V-04)*

Planned commands (see `Docs/CONTRIBUTING.md` §4):

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
make setup && make test
make demo        # the one command every reported number comes from (seed 42)
make app         # Streamlit dashboard
```

## Assumptions and cost-model mapping *(TBD — S-02, V-03)*

The assumption log lives in `Docs/ARCHITECTURE.md` §20 and the organizer column mapping template in `Docs/DATABASE.md` §8. Both are copied here at S-02 and finalized at V-03, with each *confirm* item marked resolved or open.

## Results *(TBD — V-04)*

To be copied from `make demo` output only. No projected numbers appear here.

## Sources

Verified, secondhand and vendor-reported claims are labelled in `Docs/TODO.md` §10 and `Docs/RESEARCH-v1.md` §H.

## Quickstart (stub)

```bash
pip install -r requirements.txt   # see Makefile
make setup && make test
make run-stub    # freshroute run --scenario tests/fixtures/tiny_3batch --policy milp --seed 42
make app         # Streamlit dashboard (shows tests/fixtures/metrics_example.json when outputs/ is empty)
```
