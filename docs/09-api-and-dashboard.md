# 09 · The API and the dashboard

The UI exists for the 10 points on explainability and commercial relevance, and for the demo. Its design is dominated by one rule: **the UI shows, the engine decides** (Rule 8). Endpoint contracts: `DATABASE.md` §11. Layers: `ARCHITECTURE.md` §16.

## The three layers

```
frontend/ (React, TypeScript)  ──HTTP──►  freshroute/api/ (FastAPI)  ──►  runs.runner.run / runs.ladder.run_ladder
 renders JSON verbatim                     serves outputs/ verbatim           writes outputs/<run_id>/
```

- **The frontend** renders what it is given. The only arithmetic allowed is a display delta between two stored numbers, and it lives in one helper (`frontend/src/lib/delta.ts`).
- **The API** serves run files unchanged. It may *start* a run. It never sums, averages or derives a KPI (D-18).
- **The engine** writes files. Those files are the single source of every number on screen.

The payoff is traceability: any figure shown to a judge can be proven by opening a named file in `outputs/`. It also means a UI bug can show the wrong thing but can never compute the wrong thing.

## Running a plan from the UI (D-21)

`POST /api/runs` returns immediately with HTTP 202 and enqueues the run. One worker thread runs jobs one at a time, so two HiGHS solves never compete for the same laptop. Status is kept in `outputs/.api/jobs/<run_id>.json`. A run is "done" when `metrics.json` exists on disk, so the state survives an API restart. While the solver is still improving, the status also carries `progress` (`version`, `net_inr`, `final`, `elapsed_s`); every version is a complete run directory, so the dashboard shows the first plan after a second or two, reloads it as better plans appear (banner "Showing the best plan found so far") and shows the final result when the state turns `done`.

## One URL for the demo (D-20)

In development, `make api` (port 8000) and `make web` (Vite on 5173, proxying `/api`) run side by side. For the demo, `make serve` builds the SPA and FastAPI serves `frontend/dist` from the same origin: one command, one URL, no CORS.

## What the user sees

The frontend has two parts, switched by URL hash (D-32): a narrative **landing page**, and an **operations dashboard** with four tabs: 1. Results, 2. Today's plan, 3. What if something breaks? (the route map where a road can be closed live, plus the replan diff) and 4. Proof & audit. Results shows baseline against ours on food spoiled, orders filled, profit after all costs and rule breaks, plus the waterfall ("Where the extra profit comes from") and the ladder ("Every rule vs FreshRoute"). Proof & audit shows the validator panel, assumptions and `run_manifest.json`.

A synthetic-data banner is driven by `scenario.json → source` and is shown whenever the data is synthetic (Rule 7).

Types in `frontend/src/types.ts` mirror `DATABASE.md` §11; add a field to one and you add it to the other in the same change. If an endpoint shape changes, bump `api_version`.

## Gotchas

- Only one API server can bind port 8000 at a time. Stop the dev server before `make serve`.
- Missing files appear as absent keys, never as invented values. If a panel is empty, check that the run directory has the file.
- Animations respect `prefers-reduced-motion`.
- `ARCHITECTURE.md` §16 describes the dashboard; if the page structure changes, update that section in the same change.
