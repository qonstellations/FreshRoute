# DECISIONS.md

Decision log for FreshRoute. `D-xx` = decision (this file); `A-xx` = assumption (`docs/ARCHITECTURE.md` §20). Add the next free `D-xx` at the bottom; never renumber. If a decision is reversed, mark it **Superseded by D-yy** rather than deleting it. D-26 is intentionally unused.

| ID | Decision | Why | Status |
|---|---|---|---|
| D-01 | Build A+ (A spine + Monte Carlo + replan + newsvendor; narrator stretch) | Highest floor; 70 of 100 rubric points are deterministic metrics | Accepted |
| D-02 | PuLP → HiGHS default; `scipy.optimize.milp` fallback | Readable constraints; both use HiGHS. Confirmed by D-14 | Accepted |
| D-03 | CSV files are the datastore; no DB server | Reproducible, diffable, trivial hidden-scenario loading | Accepted |
| D-04 | Validator re-implements the maths; shares only schema/io | Independence is what makes "0 violations" credible | Accepted |
| D-05 | MILP constraints C4/C5 indexed by arrival day | Demand and receiving capacity bind on arrival, not dispatch | Accepted |
| D-06 | `*_pct` columns hold 0–100 in files and fractions in memory; one conversion in `io.py` | Prevents the classic percent bug | Accepted |
| D-07 | Day-bucket simulator | Matches daily demand tables; simple to test | Accepted |
| D-08 | One shelf price per destination × commodity × day = discount of FEFO-head lot | Matches how a shelf label works; keeps simulator tractable | Accepted |
| D-09 | Template narration first, LLM optional | Explainability points without LLM risk | Accepted |
| D-10 | MILP must beat **FEFO** (not just FIFO) | Avoids the strawman-baseline critique | Accepted |
| D-11 | No statsforecast / demand forecasting | Out of scope; demand quantiles come from the p10/p50/p90 columns | Accepted |
| D-12 | The original 3-person role split (optimization / simulation and validation / product, UI and pitch) | Team size | Superseded by D-30 (roles and owners are no longer documented) |
| D-13 | A fixed 20 h timeline with a feature freeze before the end | Buffer before the demo | Superseded by D-30 (no schedule is tracked in the docs) |
| D-14 | Confirm D-02: PuLP 4.0.0 -> HiGHS (`pulp.HiGHS(timeLimit=, gapRel=)`) is used; `scipy.optimize.milp` (`options` `time_limit`, `mip_rel_gap`) stays the fallback; time-limit and gap options verified | `tests/test_solver_smoke.py`: both APIs give equal objectives on a toy MILP; on a hard 60x5 knapsack a 0.05 s limit returns in ~0.06 s (PuLP status `TimeLimit`, scipy status 1) and a 0.5 gap solves to Optimal. D-02 unchanged. PuLP 4.0 API differs from 3.x: build variables with `prob.add_variable(name, lb, ub, cat=)` (`LpVariable(cat=)` and `LpStatus` are gone); `solve()` returns a stats object, read `.status` against `pulp.LpSolveStatus` | Accepted |

## Toolchain, layout and UI

| ID | Decision | Why | Status |
|---|---|---|---|
| D-15 | **uv is the only Python toolchain.** `pyproject.toml` is the single dependency source and `uv.lock` is committed; `pytest`/`ruff`/`httpx` live in `[dependency-groups] dev`, never in runtime deps; every command is `uv run …`; `requirements.txt` is deleted (`uv export` only if a third party demands a file) | One resolver, one lock file, identical installs on three laptops from a fresh clone. Dev tools in runtime deps meant the demo could not be installed without the test suite. Build backend is `uv_build` with `module-root = "backend/src"`; fall back to setuptools and amend this row if packaging fights it | Accepted |
| D-16 | **Two top-level directories.** `backend/` holds everything server-side (`src/freshroute/`, `src/validator/`, `tests/`); `frontend/` holds the React app. `docs/`, `data/`, `outputs/`, and the root `Makefile`, `pyproject.toml`, `AGENTS.md`, `DECISIONS.md` stay at the root | The engine and the HTTP layer are both "backend", so a reviewer looking for server-side code looks in one place | Accepted |
| D-17 | **`validator` is installed as a second top-level package** from the same src root (`backend/src/validator/`), not a bare repo-root directory | `import validator` would only work with a `PYTHONPATH` export and `python -m freshroute.cli`. Under uv the console script `uv run freshroute` has neither, so a repo-root directory would break every installed invocation. Its import name, its independence (AST test, ARCHITECTURE §11) and the ALLOWED set are unchanged | Accepted |
| D-18 | **FastAPI (`freshroute.api`) is a thin HTTP layer over the engine.** It serves `outputs/<run_id>/` files verbatim and may enqueue `cli.run` / `ladder.run_ladder`; it never computes, derives or aggregates a KPI | The dashboard must be able to press **Plan** (ARCHITECTURE §16) without a shell, while every number stays traceable to a run directory written by the engine | Accepted |
| D-19 | **React SPA: Vite + TypeScript + recharts**, replacing Streamlit, plotly and pydeck. No SSR, no router, no state library. The component and animation libraries are D-24 and D-27; the route map is an offline SVG (no leaflet) | Static `npm run build` output is the fastest offline demo; `tsc` + build is the frontend quality gate; a router and a store would be unused by a single-page scroll experience | Accepted |
| D-20 | **One origin in the demo:** FastAPI mounts `frontend/dist` and serves the SPA, so the whole demo is `make serve` on one URL. In development, Vite proxies `/api` to `127.0.0.1:8000` | One command, one URL, nothing to start twice on stage, no CORS in the demo path | Accepted |
| D-21 | **Run triggering is asynchronous and file-backed.** `POST /api/runs` returns 202 + `run_id`; a single serialized worker thread runs the engine; status is written to `outputs/.api/jobs/<run_id>.json`; the frontend polls `GET /api/runs/{id}/status` | A practice-size MILP solve takes up to the 30 s cap, and large-scale solves take far longer (A-40). A blocking request would look like a hang. No job database and no websocket, consistent with D-03 (files are the datastore); `metrics.json` existing on disk means the run is done, so status survives a restart | Accepted |
| D-22 | **Python pinned to 3.13** via `uv python pin` (`.python-version`); `requires-python` stays `>=3.10` as a floor, but a working install needs `>=3.12` | The pinned `pulp==4.0.0` declares `Requires-Python >=3.12`, so an earlier pin (3.11) cannot install it. Downgrading pulp instead would invalidate D-14 (the PuLP 4.0 `add_variable(cat=)` API the MILP is written against), so the interpreter moves, not the solver. uv needs a single pinned interpreter to resolve and build against | Accepted |
| D-23 | Re-timed the original 20 h schedule after the toolchain and UI refactor | Replacing the UI and the toolchain was not in the original plan | Superseded by D-30 (no schedule is tracked in the docs) |
| D-24 | **Amends D-19: Mantine 9 for components, `motion` for animation** (at most two libraries, chosen by researching shadcn/MUI/Mantine/Chakra and Framer Motion/GSAP/React Spring/React Flow on 2026-10-14). Pins ≥ 2 weeks old: `@mantine/*` 9.6.3, `motion` 13.4.6 (with npm `overrides` holding `framer-motion` 13.4.6 / `motion-dom` 13.4.5 / `motion-utils` 13.3.0), Inter bundled via `@fontsource-variable/inter`, icons `@tabler/icons-react`. Springs via `<MotionConfig reducedMotion="user">`; chart bars keep recharts' own animation; map pulse is CSS | Mantine: complete component set (Drawer focus trap, NumberInput, Table sticky header, notifications) with plain CSS + PostCSS, no runtime CSS-in-JS. motion: real springs, shared-layout (`layoutId`), exit animations, count-ups. React Spring duplicates motion; React Flow loses the geography the map shows and carries a paid-to-remove badge. GSAP, rejected here, joined later under D-27 | Accepted. **Amended 2026-10-14:** the map is an offline SVG route network (motion `pathLength`), so `leaflet`/`react-leaflet` were removed. **Amended by D-27:** GSAP added for scroll choreography |
| D-25 | **Synthetic-data ruling.** The organizers confirmed all datasets may be synthetically generated, so the open questions about their material resolve to team-confirmed defaults (see "Default rule" below): cost model = ARCHITECTURE §7 (extended by D-28), no organizer baseline (`organizer_baseline` stays planned, `fefo` stays the comparison baseline), `plan.csv` + manifest is the submission format, the hidden suite is team-designed (D-29), absolute epoch by default, validator codes as built, rail / P10–P90 / events are in-schema and used. Only pitch length, live-vs-video and venue still need a real organizer answer (assume 3:00 and an offline demo). Rule #1 still applies the moment any real organizer material appears | No hidden format to discover; waiting on organizer material would block the team indefinitely. Recording the ruling lets everything proceed on our own schema | Accepted |
| D-27 | **Amends D-24: GSAP 3.12.5 joins for scroll choreography** (ScrollTrigger reveals/parallax/marquee, ScrollToPlugin anchor nav). The Atelier-style reference look needs scroll-linked storytelling; motion stays for component springs (drawer, count-ups, button states). Pin `gsap@3.12.5` exact. Reduced-motion users get a static page. The UI is one scroll page with sections Plan, Score, Trucks, What if and Trust; engine and API are untouched. Look: Anton display + Kode Mono labels (bundled via `@fontsource/anton@5.2.5`, `@fontsource/kode-mono@5.2.5`, exact pins; offline-safe), cream `#fef0d5` paper, sharp hairline rectangles (`defaultRadius: 0`), blue-block CTAs with slide-up hover, doubled outline/solid titles wiped in on scroll, dark Trust section, footer meta grid + BACK TO TOP[↑]. Ink is vegetable green `#1f7a4d` (`#4fbf7f` on dark); theme toggle (cream / deep-green `#10241a`, remembered as `fr-theme`); contrast audited (solid-ink score/robustness bands, readable Trust tables, theme-following navbar, explicit footer grid spans). Implementation: `gsap.context` scope + revert, `matchMedia`, batched reveals, ordered refresh | Atelier-style scroll experience without re-implementing scrub/pin math on motion; one focused library addition, no backend impact | Accepted |
| D-28 | **Procurement is part of net ₹ (schema_version 2).** `net = revenue − cost_of_goods_sold − transport − handling − spoilage_cost`, where `cost_of_goods_sold = sold_kg × unit_cost_inr_kg` (`costmodel.cost_of_goods_sold`). Spoilage cost still equals `unit_cost + disposal − salvage` per spoiled kg; stock alive at horizon end is inventory held at cost (carry-over, valued 0, no COGS). New `costmodel` functions: `demand_uplift`, `salvage_cap_frac`, `cost_of_goods_sold`, `shipped_margin` (the MILP and `feasibility.margin_inr_kg` use it). `metrics.json → economics_inr` gains `cost_of_goods_sold`; the waterfall gains the step "Cost of extra goods sold" (6 delta steps); `SCHEMA_VERSION` is 2 in `config.py` and the validator. See A-48 | Without procurement cost, selling more always looked profitable and net ₹ was not a margin a business could recognise; with it, shipping a kg that only sells at a loss is visibly worse than leaving it, and the spoilage cost is no longer the only place the unit cost appears | Accepted |
| D-29 | **Synthetic generator v3 for realism.** Real node names and coordinates (hubs Kolar and Chikkaballapur; destinations `D1`–`D8`), lane time from road distance, rail only to far destinations, outlet type driving window / price / basket / capacity, demand ≈ supply and only on reachable days, per-commodity shelf-life parameters that make expiry bind for the perishables, Beta remaining life, and a fleet whose trips per day follow lane times. `price_source = static_table_generator_v3`. Tuned for plausibility via the quality tests in `backend/tests/test_generator.py`, not calibrated to NABCONS (A-47, A-49). Regenerate with `freshroute generate` | The earlier generator produced fake coordinates, unreachable demand and unrealistic fleets, so scores on it said little. The NABCONS "calibration" it claimed was circular (knobs tuned to the number they were then checked against) | Accepted |
| D-30 | **Docs describe the current state only.** Task-tracking documents, task / gate / phase / hour IDs and the owner scheme are removed; the repo documents what exists, what is planned-not-built is labelled as planned, and measured numbers are not frozen into prose (docs give the command that reproduces them). Commits use `type(scope): summary` | A tracker in the docs goes stale the moment work lands, and stale IDs and figures contradict the code | Accepted |

## Open decisions

These stay open until the organizers publish their material:

- Organizer cost model vs ours: which coefficients change?
- Window mode (absolute vs daily), horizon, origin handling cost, hard-violation definition.
- Whether `data/organizer/` may be committed.
- Whether AI coding assistants and external data are permitted by the event rules.

### Organizer material: what exists

Audited 2026-10-14. **No organizer material exists anywhere the team can reach**, so the work that depends on it cannot be done, not merely undone:

| Item | Evidence checked | Outcome |
|---|---|---|
| `data/organizer/` (rubric, dataset, baseline, submission format) | directory has never been created in the repo; `.gitignore` only excludes it | **absent** |
| Organizer credentials | no `.env`, no key in the environment | **absent** |
| Agmarknet snapshot | `api.data.gov.in` rejects the published sample key with `{"error": "Key not authorised"}`; a registered key is required | **absent** |
| The organizers' own baseline | the team's problem-understanding note asks, unanswered, "Is a baseline supplied by the organizers? If so, implement that baseline exactly", and warns that its example baseline is "only an example" | **unknown** |

Consequences, all deliberate: the organizer mapping table (`DATABASE.md` §8) cannot be filled and `organizer_baseline` cannot be implemented "exactly from the organizers' doc". Inventing one and labelling it official would be the one failure rule #1 exists to prevent, so `ladder.json → official_baseline` stays `null` and the waterfall's baseline stays `fefo` (asserted by `tests/test_ladder.py`). **Unblock trigger:** the organizers publish the material → re-read it → fill `DATABASE.md` §8, settle the open decisions above, then implement the adapter and `organizer_baseline` against the real procedure.

## Default rule: if unspecified, we proceed like this

The open decisions above stay open until the organizers' material answers them. **Until then, and for anything the organizers do not specify, the team proceeds with these defaults** and builds so each can be changed in one place (`config.py`, `costmodel.py` or the adapter):

- **Cost model:** our `docs/ARCHITECTURE.md` §7 (with D-28). The organizers' model overrides it the moment it is known (non-negotiable 1 in `AGENTS.md`).
- **Window mode / epoch:** absolute hours from day 0 at 00:00 (A-01); the generated scenarios set `window_mode = daily` explicitly.
- **Horizon end:** unexpired stock is carry-over, valued 0, not spoiled (A-06).
- **Origin handling cost:** 0 (A-07).
- **Hard violations:** the codes in `validator/` as built.
- **Organizer data:** `data/organizer/` is git-ignored and never committed.
- **AI assistants / external data:** use is allowed (a human reviews every merge) until the event rules say otherwise; if they forbid it, stop and flag it.
- **Other open questions:** baseline, submission format, hidden scenarios, rail / P10 / P90 / events presence, pitch and venue rules are open on the same terms.
- **`remaining_shelf_life_h` (A-03):** measured at `available_from_h` in reference-temperature-equivalent hours, as `docs/ARCHITECTURE.md` §7.
- **Event semantics (A-14):** as `docs/DATABASE.md` §6.
- **Anything else:** the author decides, records an `A-xx` or `D-xx`, and moves on.

When an open decision is resolved, add the next free `D-xx` row and update the matching `A-xx`; the default above is then superseded.
