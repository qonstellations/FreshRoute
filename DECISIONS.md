# DECISIONS.md

Decision log for FreshRoute. `D-xx` = decision (this file); `A-xx` = assumption (`docs/ARCHITECTURE.md` §20). Add the next free `D-xx` at the bottom; never renumber. If a decision is reversed, mark it **Superseded by D-yy** rather than deleting it.

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
| D-13 | 20 h timeline with feature freeze at H17 | Research doc's 24 h plan freezes 3 h before the end; same buffer here | **Amended by D-23** |
| D-14 | Confirm D-02: PuLP 4.0.0 -> HiGHS (`pulp.HiGHS(timeLimit=, gapRel=)`) is used; `scipy.optimize.milp` (`options` `time_limit`, `mip_rel_gap`) stays the fallback; time-limit and gap options verified | `tests/test_solver_smoke.py`: both APIs give equal objectives on a toy MILP; on a hard 60x5 knapsack a 0.05 s limit returns in ~0.06 s (PuLP status `TimeLimit`, scipy status 1) and a 0.5 gap solves to Optimal. D-02 unchanged. PuLP 4.0 API differs from 3.x: build variables with `prob.add_variable(name, lb, ub, cat=)` (`LpVariable(cat=)` and `LpStatus` are gone); `solve()` returns a stats object, read `.status` against `pulp.LpSolveStatus` | Accepted |

## Toolchain, layout and UI refactor (RF-00 … RF-07)

The team adopted these together, before any code moved; each row is implemented by the task named in brackets.

| ID | Decision | Why | Status |
|---|---|---|---|
| D-15 | **uv is the only Python toolchain.** `pyproject.toml` is the single dependency source and `uv.lock` is committed; `pytest`/`ruff`/`httpx` live in `[dependency-groups] dev`, never in runtime deps; every command is `uv run …`; `requirements.txt` is deleted (`uv export` only if a third party demands a file) | One resolver, one lock file, identical installs on three laptops from a fresh clone. Dev tools in runtime deps (the old `pyproject.toml`) meant the demo could not be installed without the test suite. Build backend becomes `uv_build` with `module-root = "backend/src"`; fall back to setuptools and amend this row if packaging fights it | Accepted (RF-01) |
| D-16 | **Two top-level directories.** `backend/` holds everything server-side (`src/freshroute/`, `src/validator/`, `tests/`); `frontend/` holds the React app. `docs/`, `data/`, `outputs/`, and the root `Makefile`, `pyproject.toml`, `AGENTS.md`, `DECISIONS.md` stay at the root | The engine and the HTTP layer are both "backend", so a reviewer looking for server-side code looks in one place | Accepted (RF-03) |
| D-17 | **`validator` is installed as a second top-level package** from the same src root (`backend/src/validator/`), not a bare repo-root directory | Today `import validator` only works because `make` exports `PYTHONPATH` and the CLI is launched as `python -m freshroute.cli`. Under uv the console script `uv run freshroute` has neither, so a repo-root directory would break every installed invocation. Its import name, its independence (AST test, ARCHITECTURE §11) and the ALLOWED set are unchanged | Accepted (RF-03) |
| D-18 | **FastAPI (`freshroute.api`) is a thin HTTP layer over the engine.** It serves `outputs/<run_id>/` files verbatim and may enqueue `cli.run` / `ladder.run_ladder`; it never computes, derives or aggregates a KPI. This replaces the old `app/` rule | The dashboard must be able to press **Plan** (ARCHITECTURE §16) without a shell, while every number stays traceable to a run directory written by the engine | Accepted (RF-04) |
| D-19 | **React SPA: Vite + TypeScript + recharts + react-leaflet**, replacing Streamlit, plotly and pydeck. No SSR, no router, no state library | Static `npm run build` output is the fastest offline demo; `tsc` + build is the frontend quality gate; a router and a store would be unused for five tabs | Accepted (RF-05) |
| D-20 | **One origin in the demo:** FastAPI mounts `frontend/dist` and serves the SPA, so the whole demo is `make serve` on one URL. In development, Vite proxies `/api` to `127.0.0.1:8000` | One command, one URL, nothing to start twice on stage, no CORS in the demo path | Accepted (RF-05, RF-07) |
| D-21 | **Run triggering is asynchronous and file-backed.** `POST /api/runs` returns 202 + `run_id`; a single serialized worker thread runs the engine; status is written to `outputs/.api/jobs/<run_id>.json`; the frontend polls `GET /api/runs/{id}/status` | A practice-size MILP solve takes up to the 30 s cap, and A-40 measured ~4,184 s at 10x scale. A blocking request would look like a hang. No job database and no websocket, consistent with D-03 (files are the datastore); `metrics.json` existing on disk means the run is done, so status survives a restart | Accepted (RF-04) |
| D-22 | **Python pinned to 3.11** via `uv python pin` (`.python-version`); `requires-python` floor stays `>=3.10` | Matches the interpreter the team is actually developing on and keeps a newer one available for anyone who prefers it. uv needs a single pinned interpreter to resolve and build against | Accepted (RF-01) |
| D-23 | **Amends D-13: the 20-hour clock restarts at the refactor.** Feature freeze moves **H17 -> H23**; G3 H12 -> H18, G4 H15 -> H21, G6 H18 -> H24, G7 H20 -> H26. RF-01 … RF-07 (~7 h of code plus a ~1 h shared docs pass, ≈5 h of wall clock) are budgeted before Phase 3 restarts | Replacing the UI and the toolchain was not in the original 20 h plan. Re-timing is cheaper than cutting the scoreboard, map, robustness and replan surfaces, all of which the pitch script (TODO §10) and the rubric map depend on | Accepted |

## Open decisions (resolve at H0, `docs/TODO.md` S-01/S-02)

- Organizer cost model vs ours: which coefficients change?
- Window mode (absolute vs daily), horizon, origin handling cost, hard-violation definition.
- Whether `data/organizer/` may be committed.
- Whether AI coding assistants and external data are permitted by the event rules.

## Default rule: if unspecified, we proceed like this

The open decisions above stay open until the organizers' material answers them (S-01/S-02). **Until then, and for anything the organizers do not specify, the team proceeds with these defaults** and builds so each can be changed in one place (`config.py`, `costmodel.py` or the adapter):

- **Cost model:** our `docs/ARCHITECTURE.md` §7. The organizers' model overrides it the moment it is known (non-negotiable 1 in `AGENTS.md`).
- **Window mode / epoch:** absolute hours from day 0 at 00:00 (A-01).
- **Horizon end:** unexpired stock is carry-over, valued 0, not spoiled (A-06).
- **Origin handling cost:** 0 (A-07).
- **Hard violations:** the codes in `validator/` as built in F-04.
- **Organizer data:** `data/organizer/` is git-ignored and never committed.
- **AI assistants / external data:** use is allowed (human owner reviews every merge) until the event rules say otherwise; if they forbid it, stop and flag it at the next gate.
- **Full question list:** the eight S-01 questions in `docs/TODO.md` §3 (baseline, submission format, hidden scenarios, rail/P10/P90/events presence, pitch and venue rules, in addition to the four above) are open on the same terms; the README "Open questions" table tracks each one.
- **`remaining_shelf_life_h` (A-03):** measured at `available_from_h` in reference-temperature-equivalent hours, as `docs/ARCHITECTURE.md` §7.
- **Event semantics (A-14):** as `docs/DATABASE.md` §6.
- **Anything else:** the module owner decides within 5 minutes, records an `A-xx` or `D-xx`, and moves on.

When an open decision is resolved, add the next free `D-xx` row and update the matching `A-xx`; the default above is then superseded.
