# AGENTS.md

Instructions for AI coding assistants working on FreshRoute. Humans: see `docs/CONTRIBUTING.md`.

## Read first
`docs/ARCHITECTURE.md` (behaviour) → `docs/DATABASE.md` (contracts) → `docs/TODO.md` (task IDs, gates) → `DECISIONS.md`.
Reference tasks by ID (e.g. `C-01`) in commits and PRs.

## Non-negotiables
1. **Organizer cost model/data format overrides ours.** Coefficients live only in `costmodel.py`, `config.py` or the dataset. No literals elsewhere.
2. **The `validator` package is independent** (`backend/src/validator/`). It may import only stdlib, pandas, numpy, `freshroute.schema`, `freshroute.io`. It re-implements the maths.
3. **One simulator scores every policy.** Policies never compute their own reported net ₹.
4. **Deterministic.** Randomness only via `numpy.random.default_rng(seed)`; sort before iterating; same inputs ⇒ identical `metrics.json`.
5. **The LLM never decides.** HiGHS decides; an LLM may only parse a sentence into a pydantic-validated event or narrate JSON it was given.
6. **Never crash on a scenario.** Soft constraints, solve time limit, FEFO-greedy fallback.
7. **Measured numbers only**; synthetic data labelled synthetic. Do not present projected rubric scores as results.
8. **The UI shows, the engine decides.** `freshroute/api` (FastAPI) serves `outputs/` files verbatim and may enqueue `cli.run`/`ladder.run_ladder`; `frontend/` (React) renders the JSON it is given. Neither computes a KPI — a display delta between two stored numbers is the only exception and lives in one helper.
9. **Add-ons are flags**, removable without breaking the spine.

## Conventions
- Layout: `backend/src/freshroute/` (engine + `api/`), `backend/src/validator/`, `backend/tests/`, `frontend/` (React). `docs/`, `data/`, `outputs/` at the root.
- Python 3.10+ floor, developed on the version pinned in `.python-version`; ruff, type hints on public functions.
- uv owns Python: `uv sync` to install, `uv run …` to execute, `uv lock` to resolve. No `pip`, no `requirements.txt`.
- Unit suffixes: `_kg _h _inr _inr_kg _c _pct` (0–100) `_frac` (0–1). Percent→fraction conversion only in `io.py`.
- Column names from `schema.py` constants; frontend types mirror `docs/DATABASE.md` §11.
- Tolerance: `FLOAT_TOL` from `config.py`, never `==` on floats.
- Each module starts with a short docstring naming the `ARCHITECTURE.md` section it implements.

## Workflow
- Run `make check` (ruff + pytest + frontend build + validate demo plan) before proposing a commit.
- Changing a contract (tables, JSON, CLI, API endpoint, function signatures) means updating the doc in the same change, and bumping `schema_version` (data format) or `api_version` (endpoint shape) if a format changed.
- New assumption → next free `A-xx` in `docs/ARCHITECTURE.md` §20. New decision → next free `D-xx` in `DECISIONS.md`.
- Commits: `type(scope): summary (TASK-ID)`. Keep changes small, one task per change.
- Never commit `.env`, keys, `.venv`, `node_modules/`, `frontend/dist/`, `outputs/` (except `outputs/demo_backup/` at freeze) or restricted organizer data. Commit `uv.lock` and `package-lock.json`.
- After feature freeze (H23): bug fixes only.

## Out of scope
statsforecast/demand forecasting, the agentic Copilot stack, DP markdown, OR-Tools routing, live API calls in the demo, a database server, authentication, SSR/routing for the SPA, a global state library.
