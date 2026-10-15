# Submission guide

How to get FreshRoute ready to hand in, and what we do **not** know yet. The organizers have published no submission format, deadline or rubric beyond `docs/PS.md`, so this page records our defaults and the open questions. When the organizers answer, update this page and `DECISIONS.md` (D-25 and the "Open decisions" list).

## What we hand over

Our default submission format (D-25) is the run directory of the final plan:

| File | What it is |
|---|---|
| `plan.csv` | The recommendation: which batch goes where, when, on which vehicle |
| `trips.csv` | Vehicle trips |
| `discounts.csv` | Markdown schedule (empty for FreshRoute's own plan; filled by the `last_day_50` baseline) |
| `metrics.json` | Spoilage, fulfilment, net ₹, violations, economics |
| `validation.json` | Independent validator report |
| `run_manifest.json` | Seed, git SHA, scenario hash, solver status |
| `dispatch_sheet.csv` / `.txt` | Per-vehicle, priority-ordered instructions |
| `reason_cards.json` | Why each shipment and discount was chosen |

Also in the repository: the ladder and waterfall (`outputs/demo_backup/practice__ladder__s42/`), the README, and these docs. File formats are in `DATABASE.md` §5.

## Pre-submit checklist

Run these in order, from a clean checkout of the exact commit you are submitting.

1. `git status` is clean, and `git pull --ff-only` is up to date.
2. `make setup`
3. `make check`. It must be green: ruff, pytest, frontend build, and zero violations on the demo plan.
4. `make demo`. Compare the headline numbers with the README results table. If they differ, find out why before doing anything else (see `10-determinism-and-reproducibility.md`).
5. `make serve`, open `http://127.0.0.1:8000`, run a plan from the UI, and check the scoreboard and trust tab load.
6. Confirm `outputs/demo_backup/` is committed and current. It is the offline fallback.
7. Confirm nothing forbidden is committed: `.env`, keys, `.venv`, `node_modules/`, `frontend/dist/`, other `outputs/`, and restricted organizer data.
8. Tag or note the commit SHA you submitted.

## Running a hidden scenario

If the organizers give a scenario in our format, drop it in `data/scenarios/<name>/` and run:

```bash
uv run freshroute run --scenario data/scenarios/<name> --policy milp --seed 42 --fail-on-violations
```

The `--fail-on-violations` flag exits non-zero if the validator finds any hard violation. The run never crashes on odd data; if the solver has no incumbent it falls back to FEFO-greedy and says so in the manifest (check `fallback_used`).

If their data is in a different format, the adapter (`adapters/organizer.py`) is **planned but not built**, and `DATABASE.md` §8 holds the blank mapping template. Map their columns to ours there first.

We built our own hidden-style suite for practice: `hidden_small`, `hidden_practice`, `hidden_3x`, `hidden_10x`, five `hidden_ev_*` event scenarios and `hidden_edge`. Run a couple before submitting; they exercise scale and odd cases.

## Open questions for the organizers

- Official cost model and baseline (theirs overrides ours; Rule 1).
- Submission format, deadline, and where to upload.
- Pitch length and whether the demo is live or recorded (we assume 3:00 and an offline demo).
- Whether AI assistants and external data are permitted.
- Delivery-window semantics: `absolute` or `daily`.
- Whether organizer data may be committed to the repository.

## Offline fallbacks (the venue Wi-Fi will fail)

- Everything runs locally; no live API is used (invariant 10).
- If the live run is slow: show `outputs/demo_backup/`.
- If the frontend breaks: the CLI `make demo` output is a complete scoreboard.
- If the solver misbehaves: the fallback plan is built in, and the banner says so.
