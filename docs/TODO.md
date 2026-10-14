# TODO.md

**FreshRoute — Plan A+ · 20-hour build · team of 3**
Check items off as they land on `main`. Task IDs are stable — reference them in commits and PRs.

> Companion docs: `ARCHITECTURE.md` (how it works) · `DATABASE.md` (data contracts) · `CONTRIBUTING.md` (how we work).
> **Rule #1: the organizers' cost model and dataset format override ours.** S-02 exists to make that mapping explicit.
> **ID legend:** `PRE` pre-event · `S` scaffolding · `F` foundations · `C` core engine · `RF` toolchain/UI refactor · `U` product surface · `AD` A+ add-ons · `H` hardening · `V` wrap-up · `R` release/rehearsal · `G0–G7` gates. **`A-xx` always means an *assumption*** (`ARCHITECTURE.md` §20) and `D-xx` a *decision* (`DECISIONS.md`) — never a task.

> **Clock (D-23):** the 20 h clock restarts at the refactor (Phase 2.5, ~5 h of wall clock / ~8 person-hours). Every gate after G2 shifts by six hours: **G3 H12 → H18, G4 H15 → H21, G5 (freeze) H17 → H23, G6 H18 → H24, G7 H20 → H26.**

---

## 0. Roles

| Role | Person | Owns |
|---|---|---|
| **P1 — Optimization lead** | Aarush | shelf-life maths, feasibility filter, MILP, replan, reason-card fields, LLM narrator (stretch) |
| **P2 — Simulation, metrics & validation** | Omcar | repo/CLI skeleton, cost model, simulator, metrics, independent validator, baselines, ladder, Monte Carlo, newsvendor, determinism/perf |
| **P3 — Product, UI & AI/pitch** | Pratham | generator/adapter, discount rule, React frontend, dispatch sheet, template narration, deck, demo script, video |

(Research doc's 4-role plan merged for a team of 3: UI + product/pitch + AI = P3.)

---

## 1. Timeline at a glance

Phases 0–2 are done (G2 passed). The toolchain/UI refactor sits between them and Phase 3, and shifts every later gate (D-23).

| Phase | Hours | Name | Gate at end |
|---|---|---|---|
| 0 | H0–H2 | **Scaffolding & contracts** | **G0** (H2) |
| 1 | H2–H5 | Foundations: validator, metrics, simulator, feasibility, generator | **G1** (H5) |
| 2 | H5–H9 | Core engine: MILP, markdown, baselines, ladder | **G2** (H9) |
| 2.5 | H9–H14 | **Toolchain & UI refactor** (uv, `backend/`+`frontend/`, FastAPI, React) | no gate — `make check` green |
| 3 | H14–H18 | Product surface + spine hardening | **G3** (H18) — tag `v0.1-spine` |
| 4 | H18–H21 | A+ add-ons: stress test, replan, newsvendor | **G4** (H21) |
| 5 | H21–H23 | Hardening, dry runs, **FEATURE FREEZE** | **G5** (H23) — tag `v1.0-freeze` |
| 6 | H23–H24 | Backup video, README, final numbers | **G6** (H24) |
| 7 | H24–H26 | Fresh-clone test, rehearsal ×3, submission | **G7** (H26) |

Budget: the clock is ~26 h for 3 people (~78 person-hours, up from 60). Research-doc rule of thumb: ~40 % engine/simulation/validation, ~25 % UI, ~15 % robustness & replan, ~20 % pitch/demo hardening/docs. Do a 10-minute checkpoint at every gate (what's green, what's red, cut or continue).

Hours per person per phase (estimates; P1 20.5, P2 24, P3 24):

| | P0 | P1 | P2 | RF | P3 | P4 | P5 | P6 | P7 |
|---|---|---|---|---|---|---|---|---|---|
| P1 | 2.0 | 3.0 | 4.0 | 0.5 | 3.0 | 3.0 | 2.0 | 1.0 | 2.0 |
| P2 | 2.0 | 3.0 | 4.0 | 4.0 | 3.0 | 3.0 | 2.0 | 1.0 | 2.0 |
| P3 | 2.0 | 3.0 | 4.0 | 3.5 | 3.0 | 3.0 | 2.0 | 1.0 | 2.0 |

The `RF` column is the refactor code work (Phase 2.5): P2 4.0 h, P3 3.5 h. P1 only reviews it. Add ~1 h shared for the RF-00 docs pass that everyone signs off.

P1's Phase 5 figure includes up to 1.0 h for the optional AD-09 stretch; if AD-09 is dropped at G4, that hour becomes bug-fix buffer, not new scope.

Plan one real meal break around H8–H9 and a short break roughly every 4 h. Nobody codes alone for more than 45 minutes while stuck.

---

## 2. Before H0 (pre-event)

- [x] **PRE-01** · all — ~~Agree on one Python version; everyone installs the deps and confirms a toy MILP through both solver APIs.~~ **Done 2026-10-14.** Interpreter: **3.13** (D-22, corrected — see below). Verified on this machine: `uv venv --python 3.13` → `uv pip install -e . -r requirements.txt` resolves every pin (scipy, pulp 4.0.0, highspy, pandas, numpy, pydantic, pytest, ruff); `pytest` = **117 passed, 1 xfailed**; `ruff check .` clean; the toy MILP solves through **both** PuLP→HiGHS and `scipy.optimize.milp` with working time-limit and gap options (`tests/test_solver_smoke.py`, 4/4). **Finding:** the D-22 pin of 3.11 was wrong — `pulp==4.0.0` declares `Requires-Python >=3.12`, so the pinned dependency set is unsatisfiable on 3.11. D-22 corrected; the solver stays (downgrading pulp would invalidate D-14). Node 26 / npm 11 present for RF-05.
- [x] **PRE-02** · P3 — ~~Download an Agmarknet CSV snapshot.~~ **Closed on the documented fallback, 2026-10-14.** No `data.gov.in` API key is available to the team and the published sample key is dead (`{"error": "Key not authorised"}`), so no snapshot was taken and **no price data was invented**. The fallback this task itself specifies is already live: the generator's static price table (A-30, `price_source = static_table_generator_v1`), so A-20 does not apply to practice data. Resource ids, filter-parameter casing and the `DATAGOV_API_KEY` procedure are recorded in `DATABASE.md` §9, making this a 10-minute job if a key appears; `scripts/build_prices.py` is still to be written then. *This needs a credential, not time — it cannot be unblocked by working harder.*
- [x] **PRE-03** · P3 — ~~Re-verify every ₹ crore figure against the official source.~~ **Done 2026-10-14**; the verified table is now the README "Sources" section. Every figure the pitch uses was checked against a primary source: NABCONS/MoFPI study scope (**54 commodities, 15 agro-climatic zones, 292 districts** — PIB PRID 2148529 / 2151371 and the study report); tomato **8.37 % + 3.25 %** and onion **5.31 % + 1.96 %** (PIB PRID 2151371, Annexure-II); fruits **6.02–15.05 %**, vegetables **4.87–11.61 %** (MoFPI annexure, Lok Sabha USQ 2998); cold storage **8,815 units / 402.18 lakh MT as of 30 June 2025** (PIB PRID 2172351). **Correction:** the tomato loss value is ₹**5,921.15** crore per **Lok Sabha Unstarred Q 2138, 12 Feb 2026** (24.59 lakh MT) — a stronger source than the PIB release previously cited, and it settles the open question: it *is* an annual estimate, so "a year" may be said. It still covers all stages, not the 3.25 % market slice.
- [ ] **PRE-04** · all — Choose the **demo laptop**; test HDMI/projector; install a screen recorder; confirm everything runs with Wi-Fi off. **Needs a human and the hardware, not code — still open.** With the refactor it becomes: pick the laptop · `make serve` on it with Wi-Fi off · screen recorder installed · `npm ci && npm run build` verified on that machine (Node 22+, R-02) · `outputs/demo_backup/` present. Re-check at H-04 and R-02.
- [ ] **PRE-05** · all — Read `ARCHITECTURE.md`, `DATABASE.md`, `CONTRIBUTING.md`. Sleep. **Needs the three humans — still open.** The docs were checked for internal consistency on 2026-10-14 during RF-00 (no document describes a layout, dependency or gate that contradicts another). Each person signs off at the next checkpoint.
- [x] **PRE-06** · P1 — Only if you expect to attempt AD-09: decide the LLM provider and put the API key in an environment variable. **Not triggered; decided 2026-10-14.** AD-09 is gated on G4 (now H21, five gates away) and is cut-list item 1, so choosing a provider and holding a key now is speculative work on the first thing we would cut. Revisit at the G4 go/no-go; the key goes in `.env` as `LLM_API_KEY`, never in git. Template narration (AD-07) is the default path meanwhile.

---

## 3. Phase 0 — Scaffolding & contracts (H0–H2)

Goal: by H2 everyone can run `make setup && make test && make run-stub` and open the dashboard, and the written contracts are signed off. No feature code before G0.

- [ ] **S-01** · all · 0.5 h — **Read the organizers' material** (rubric, dataset, baseline, cost model, submission format, rules) and answer the **open questions** below in writing. **BLOCKED, audited 2026-10-14: the material does not exist on any team machine.** Checked: `data/organizer/` has never been created; no `.env` or organizer credential anywhere; the team's own problem-understanding note still lists the organizers' baseline as unanswered ("Is a baseline supplied by the organizers? If so, implement that baseline exactly") and warns its example baseline is "only an example". Evidence table in `DECISIONS.md` → "Blocked on 2026-10-14". The eight questions below stay open on the default rule meanwhile. *Unblocks when the organizers publish it.*
- [ ] **S-02** · all · 0.5 h — **Contract sign-off.** Fill the mapping table (`DATABASE.md` §8) into the README; compare the organizers' cost model with `ARCHITECTURE.md` §7 and list every coefficient or formula in `costmodel.py` / `config.py` that must change; confirm discount rule, hard-constraint list, window mode, horizon, origin handling cost; copy the assumption log (`ARCHITECTURE.md` §20) into the README and mark each **confirm** item resolved or still open. *Done when:* a commit `docs: sign off cost model and contracts` exists and all three agree. **Half done 2026-10-14.** Mechanical parts **complete**: mapping table copied into the README, the 18-row cost-model comparison is written against every §7 coefficient, and the assumption log is now copied in full (A-01 … A-40 — it previously stopped at A-22), with every `confirm` item marked still open. **Still blocked:** the comparison can only be *signed off* against real organizer material, and the three signatures are the humans' to give. *Unblocks with S-01.*
- [x] **S-03** · P2 · 1.0 h — **Repo skeleton.** Create the layout in `ARCHITECTURE.md` §5, `Makefile` (`setup test check demo app run-stub`), `pyproject.toml`/`requirements.txt` with pinned versions, `.gitignore` (outputs, data/organizer, `.env`, `.venv`), ruff + pytest config, `config.py`, `schema.py` (column-name constants), CLI skeleton so `freshroute run --scenario X --policy milp --seed 42` writes a stub `metrics.json`, plus the **input CSVs for `tests/fixtures/tiny_3batch/`** (3 batches, 2 destinations, 1 vehicle; valid per `DATABASE.md`; expected outputs come at F-04). *Done when:* `make test` passes with one placeholder test and `make run-stub` loads the fixture. *(The `Makefile` targets, `requirements.txt` and the layout in this task are superseded by RF-01/RF-03.)*
- [x] **S-04** · P1 · 1.0 h — **Solver smoke test + decision D-02.** Solve a toy MILP via PuLP→HiGHS and `scipy.optimize.milp`; verify the **time-limit and MIP-gap options actually work** in the chosen API; record the decision. Create `shelflife.py` with the `decay` / `usable_life_at_arrival` signatures and a stub test of the worked example (`ARCHITECTURE.md` §7.1).
- [x] **S-05** · P3 · 1.0 h — **Dashboard shell** that renders from `tests/fixtures/metrics_example.json` (hand-written from `DATABASE.md` §5.7). Add a README quickstart stub. *Done when:* the dashboard shows placeholder KPI tiles. *(Built in Streamlit; replaced by RF-05 — React shell against `GET /api/runs`.)*

**Open questions to resolve at H0** (S-01):
1. Exact cost model: revenue, transport, handling (incl. any **origin** handling), spoilage and disposal, how discounts are accounted.
2. The organizers' baseline: documented procedure and how it is scored.
3. Submission format for plans and whether a scoring/checker script is provided.
4. Hidden scenarios: same file format as the dataset? How large? Which events? Horizon?
5. Time conventions: epoch, whether delivery windows are absolute or repeat daily.
6. What counts as a hard-constraint violation.
7. Rules: are AI coding assistants / external data / open-source libraries allowed? Pitch length (we assume 3:00) and live-demo vs video requirements; venue network and hardware.
8. Are rail lanes, P10/P90 columns and events present in the real data?

**Gate G0 (H2):** cost model signed off in writing · `make setup && make test && make run-stub` work on all three laptops and the dashboard opens · `tests/fixtures/tiny_3batch/` inputs and `metrics_example.json` committed · open questions answered or logged as assumptions.
*If red:* do not start Phase 1 work that depends on the missing contract — resolve it first.

---

## 4. Phase 1 — Foundations (H2–H5)

Order matters: **validator and metrics before the optimizer.**

**P1**
- [x] **F-01** · 0.75 h — `shelflife.py` (decay, usable life) + tests incl. the worked example: usable life 87 / 69 / 13 h, third arc rejected.
- [x] **F-02** · 1.0 h — `feasibility.py`: full `arcs` table (feasible + rejected with `reject_reason`) for absolute and daily window modes, rail slots, availability, horizon. Tests per reject reason.
- [x] **F-03** · 1.25 h — MILP skeleton on `tiny_3batch`: variables `x, n, u`, constraints C1–C5, HiGHS with time limit; returns a `Plan`.

**P2**
- [x] **F-04** · 1.25 h — Hand-compute the **expected outputs** of the `tiny_3batch` fixture (inputs exist from S-03; compute by hand, with P1 checking the arithmetic) + the **independent `validator/`** (all hard-violation codes) + injected-violation tests + AST import-independence test.
- [x] **F-05** · 0.5 h — `costmodel.py` and `metrics.py` with the §5.7 invariants (mass balance, revenue/net identities) as tests.
- [x] **F-06** · 0.75 h — `simulator.py` per `ARCHITECTURE.md` §13 + hand-checked fixture result.
- [x] **F-07** · 0.5 h — `policies/fifo.py` (FIFO-nearest) + `freshroute run --policy fifo` printing the 4 KPIs.

**P3**
- [x] **F-08** · 2.0 h — **If organizer data exists:** `adapters/organizer.py` (1.5 h) + a small generator for edge/stress scenarios (0.5 h). **If not:** the full generator for all 8 tables (+ `geo.csv`), seeded, with the commodity mix and starting points in `DATABASE.md` §3.1. Output: a practice scenario with ~200 batches / 8 destinations / 3 days / 3 vehicles scale, plus a small one. (If PRE-02 was missed, use the static price table here.)
- [x] **F-09** · 1.0 h — `discount.py` as a pure function + tests on tier boundaries (`risk` 0.09 → 0 %, 0.10 → 10 %, 0.29 → 10 %, 0.30 → 20 %, 0.50 → 20 %, 0.51 → 35 %; boundary convention is assumption A-22), the 24 h time trigger (35 % stays 35 %), max-discount cap, salvage floor, worth-it test, monotonicity.

**Gate G1 (H5):** validator + metrics tests green on the hand-computed fixture · `freshroute run --policy fifo` prints spoilage, fulfillment, net ₹, violations · feasibility table works on the practice scenario · generator/adapter emits all tables and loads without errors.

---

## 5. Phase 2 — Core engine (H5–H9)

**P1**
- [x] **C-01** · 1.5 h — Full MILP objective per `ARCHITECTURE.md` §9.2 (revenue, variable transport, fixed trip cost, destination handling, λ·spoilage, FEFO tie-break, unshipped-expiry penalty).
- [x] **C-02** · 1.0 h — Soft constraints + penalty slacks, 30 s limit returning the incumbent, **fallback to FEFO-greedy** if no incumbent, slack usage and `fallback_used` in the manifest.
- [x] **C-03** · 1.0 h — Plan/trips export (`plan.csv`, `trips.csv`, first-fit trip loading), priority score and ordering, C6 balance constraint, and the **`demand_cap_override` hook** for the newsvendor.
- [x] **C-04** · 0.5 h — **MILP ↔ simulator consistency test** (overship 0, markdown off, p50 realization ⇒ simulator net equals MILP objective without tie-break/slack terms).

**P2**
- [x] **C-05** · 0.75 h — `policies/fefo.py` (FEFO-greedy over feasible arcs, same demand caps) and `policies/last_day_50.py`.
- [ ] **C-06** · 1.0 h — `policies/organizer_baseline.py` implemented exactly from the organizers' doc + export of plans in the organizers' submission format. **BLOCKED on S-01: there is no organizer doc, so "exactly" cannot be honoured.** Re-confirmed 2026-10-14 — the team's problem-understanding note still lists the organizers' baseline as an open question and explicitly says the note's own example baseline is "only an example; the competition's prescribed baseline should take precedence if one is supplied". Writing a guessed baseline under the name `organizer_baseline` would be the exact failure rule #1 exists to prevent, so it is **not** being written. The blocked state is implemented and tested instead: `ladder.json → official_baseline` is `null`, the waterfall's baseline is `fefo` (`ladder.py:13,46`), and `tests/test_ladder.py` asserts the null. Until it lands: `ladder.json` has `official_baseline: null`, the waterfall baseline is `fefo`, and `--policy organizer_baseline` fails with an explicit C-06 message instead of a bare "unknown policy". *Unblocks with S-01.*
- [x] **C-07** · 1.25 h — `ladder.py`: `fifo → fefo → milp → milp_markdown` through the same simulator, `ladder.json`, `waterfall.json` with the **reconciliation test** (±₹0.01).
- [x] **C-08** · 0.5 h — `run_manifest.json` + **determinism test** (same seed ⇒ identical `metrics.json`).
- [x] **C-09** · 0.5 h — Perf harness: generate a 10× scenario and time plan solves (feeds U-02 and the performance budget).

**P3**
- [x] **C-10** · 1.0 h — Calibrate the generator so the FIFO baseline's market-stage spoilage lands near NABCONS tomato ≈ 3.25 % and onion ≈ 1.96 % (sanity check — A-21), so the baseline is plausible, not a strawman.
- [x] **C-11** · 0.75 h — Wire the **`milp_markdown`** pipeline: plan → `discount.py` → `discounts.csv` → simulator (with P1/P2).
- [x] **C-12** · 1.5 h — Scoreboard: 4 KPI tiles (spoilage kg and %, fulfillment %, net ₹, violations baseline n vs ours), min fill rate, validator panel, "synthetic data" banner — all read from `outputs/`.
- [x] **C-13** · 0.75 h — Reason-card text templates + dispatch-sheet skeleton.

**Gate G2 (H9):** on **3 seeds**, `milp` has higher net ₹ than **FEFO** (not just FIFO) and is not worse on spoilage · independent validator reports **0 violations** for `milp` and `milp_markdown` · plan → simulator → metrics → scoreboard works · consistency test C-04 passes.
*If MILP does not beat FEFO:* check objective coefficients against the simulator (C-04) before touching anything else; do not start Phase 4 until the spine wins.

*G2 result (2026-10-14, synthetic data, base realization, quiet machine):* **passed** on practice (seed 42) and 3 generated practice-size scenarios (seeds 1–3). Spoilage kg / net ₹, fefo → milp: practice 1,342 / 1,413,264 → 1,244 / 1,655,781 · s1 1,857 / 1,682,657 → 1,311 / 1,793,291 · s2 2,134 / 1,385,359 → 1,620 / 1,510,745 · s3 2,350 / 1,421,459 → 2,289 / 1,535,890. Validator 0 violations for `milp` and `milp_markdown` on all four; C-04 passes; scoreboard renders the `milp_markdown` run with deltas vs fefo. Caveats: A-39 (generated `small` seed 1 is an `xfail` on spoilage), A-37 (markdown near-inert), A-40 (time-limited solves are load-dependent; 10× scale far over budget).

---

## 5b. Phase 2.5 — Toolchain & UI refactor (RF-00 … RF-07, ~8 h)

Decisions D-15 … D-23 in `DECISIONS.md`; target-state behaviour in `ARCHITECTURE.md` §5/§16/§17; API contract in `DATABASE.md` §11. **Docs land first (RF-00), then code, one task per commit.** The engine is not modified: the acceptance test is that `metrics.json` for `tiny_3batch` and `practice`, seed 42, is byte-identical before and after.

- [x] **RF-00** · all · 1.0 h — **Docs pass.** Rename `Docs/` → `docs/`; rewrite `ARCHITECTURE.md` §2/§3/§4/§5/§6/§11/§16/§17/§18/§19/§21/§22/§23; add the HTTP API contract as `DATABASE.md` §11; update `CONTRIBUTING.md` §2/§4/§5/§6/§7/§8/§11/§13, `AGENTS.md`, `README.md`, `DECISIONS.md` (D-15 … D-23) and this section. *Done when:* no doc describes Streamlit, `app/`, `requirements.txt` or the old layout.

**P2**
- [x] **RF-01** · 0.5 h — **uv.** `uv python pin 3.13` (D-22; this line first said 3.11); `pyproject.toml` → runtime deps without `streamlit`/`pydeck`/`plotly`, plus `fastapi`/`uvicorn`; `[dependency-groups] dev = [pytest, ruff, httpx]`; build backend `uv_build` with `module-root = "backend/src"`; `uv lock`; delete `requirements.txt`; Makefile on `uv run`; `.gitattributes` for `uv.lock` and `package-lock.json`. *Done when:* `uv sync && uv run pytest -q` works on a fresh clone and `make check` is unchanged in result. *Done 2026-10-14 (`bc2e7f9`): `uv_build`, fastapi/uvicorn, dev group, `uv.lock`; pulp 4.0.0 needs 3.12, so `<3.12` gets `pulp<4` to keep the 3.10 floor. Fresh clone: `uv sync && uv run pytest -q` → 123 passed, 1 skipped (Streamlit AppTest until RF-02), 1 xfailed.*
- [x] **RF-03** · 1.25 h — **Split directories** (D-16, D-17). `git mv src backend/src`, `git mv validator backend/src/validator`, `git mv tests backend/tests`; fix `testpaths`, `pythonpath` and ruff `src`; `parents[1]` → `parents[2]` in the six tests that reach the repo root; AST test → `backend/src/validator`. *Done when:* `uv run freshroute run …` (console script, not `python -m`) works and `import validator` needs no `PYTHONPATH`. *Done 2026-10-14 (`56a8e11`): `uv run freshroute run` and `import validator` work with no `PYTHONPATH`; `metrics.json` byte-identical for tiny_3batch (fifo, fefo, milp, milp_markdown) and practice (fifo, fefo, last_day_50), seed 42.*
- [x] **RF-04** · 1.5 h — **FastAPI** (D-18, D-21). `freshroute/api/{app,data_access,routes,schemas,jobs}.py`; every endpoint of `DATABASE.md` §11.2; `outputs/.api/jobs/<run_id>.json`; one worker thread; CORS + loopback from `config.py`; mount `frontend/dist` when it exists. *Done when:* `/docs` lists the endpoints, `POST /api/runs` returns 202 and finishes, and the scoreboard payload equals `metrics.json` byte for byte. *Done 2026-10-14: every §11.2 endpoint; `/api/runs` lists runs by output directory name (fix found in the live check: a custom `--out` dir listed but 404'd). Smoke: `POST /api/runs` small/milp_markdown → 202 → `done` in ~1 s; tiny_3batch metrics.json byte-identical.*
- [x] **RF-06** · 0.75 h — **API tests** with `fastapi.testclient.TestClient`: health, fixture fallback, run list, verbatim payload, 202 → poll → done on `tiny_3batch`, 404/400 paths, table + CSV endpoints. Replaces the Streamlit `AppTest` and the old `test_data_access.py`. *Done 2026-10-14: `backend/tests/test_api.py`, 15 tests.*

**P3**
- [x] **RF-02** · 0.5 h — **Strip Streamlit.** `git rm -r app`; delete the `AppTest`; port the `data_access` tests to the API reader. *Known cost:* no dashboard for the two commits between this and RF-05; the scoreboard comes back in RF-05. *Done 2026-10-14: `app/` removed; `data_access` lives in `freshroute.api`.*
- [x] **RF-05** · 2.0 h — **React shell** (D-19). Vite + TS strict; `src/api/client.ts`, `src/types.ts`, `src/lib/delta.ts`; `KpiTile`, `RunPicker`, `RunButton`, `ValidatorPanel`, `SyntheticBanner`, `StatusBanner`; tabs Scoreboard/Plan/Robustness/Replan/Trust. Ports **C-12** (4 KPI tiles with baseline deltas, min fill, validator panel, synthetic banner, fixture fallback) and the **C-13** render. recharts and react-leaflet land with U-08 … U-11 and AD-05. *Done 2026-10-14: React 19.3 + Vite 8.3 + TS 6.0 strict; `npm run build` clean (JS 227 kB, 71 kB gzip). Rendered through `make serve` against real `outputs/` (headless Edge screenshot). The Plan button's POST→poll loop is covered at the API level, not yet clicked in a browser.*
- [x] **RF-07** · 0.5 h — **Wiring.** `make setup` = `uv sync` + `npm ci`; `make api` / `make web` / `make serve`; `make check` adds `npm run build`; R-02 checklist gains "Node 22+"; golden-path click-through on all three laptops. *Done 2026-10-14: `make setup/api/web/serve`; `make check` adds the frontend build. Golden-path click-through on all three laptops still to do by the team (PRE-04/R-02).*

**Definition of done for the phase:** `make check` green · `metrics.json` byte-identical before/after · `grep -ri streamlit` finds nothing tracked · one URL shows the scoreboard from `outputs/` · `grep` finds no `pip install` and no `requirements.txt`.

---

## 6. Phase 3 — Product surface & spine hardening (H14–H18)

**P1**
- [x] **U-01** · 1.0 h — Reason-card fields: rejected alternatives with reason codes, chosen-vs-runner-up margin and slack (`reason_cards.json`, `DATABASE.md` §5.9). *Done 2026-10-14: `reason_cards.json` written by every run; alternatives with reason codes, `runner_up` margin, slack (DATABASE §5.9). Also fixed float `arrival_day` in discount lot ids (`B0158@D3@1.0`).*
- [ ] **U-02** · 1.5 h — **Scale test**: 10× scenario; implement the aggregation fallback (commodity × RSL bucket → disaggregate → re-check); record the measured size/time.
  *Note (2026-10-14, not ticked, SYNTHETIC):* aggregation fallback in `policies/milp.py` (`_plan_aggregated`), triggered above `AGG_ARC_THRESHOLD = 100,000` candidate arcs (practice 14,400 and fixtures unaffected: tiny_3batch fifo/fefo/milp/milp_markdown and practice milp `metrics.json` byte-identical to base). Measured with `uv run python -m freshroute.perf --scale 10 [--fleet-scale 1]`: batches-only 10× 63.8–70.5 s (53,611 vars, gap 9–14 %) → 23.2–24.3 s (14,575 vars, 505 groups, optimal, net ₹3,485,297 → ₹3,728,711); batches+vehicles 10× ~4,184 s → 251.9 s (139,159 vars, gap 43.8 %, still over the 30 s budget). Validator: 0 violations, 0 dropped lines in both. Details A-40/A-41.
- [x] **U-03** · 0.5 h — Pick and lock the **demo scenario + seed**; fix bugs found at G2.
  *Note (2026-10-14, synthetic data, base realization):* chose **`data/scenarios/practice`, seed 42** (`config.DEMO_SCENARIO` / `DEMO_SEED`). Measured with `uv run freshroute ladder --scenario data/scenarios/<x> --seed <s> --out <tmp>`. Practice s42, spoil kg / fill % / net ₹ / violations: fifo 1,785.53 / 67.05 / 1,358,102.57 / 14 · fefo 1,342.24 / 66.17 / 1,413,264.08 / 0 · milp 1,244.27 / 79.28 / 1,655,780.69 / 0 · milp_markdown 1,244.27 / 79.28 / 1,655,293.29 / 0. Waterfall fefo → milp_markdown: spoilage avoided +2,213.83, extra sales +246,771.99, transport +9,156.27, handling −15,629.65, discounts −483.23. Practice s7 gave identical KPIs (seed does not enter the base realization). Small s42 rejected: spoilage 210.77 kg for every policy and net fefo 248,859.02 → milp 256,205.56 only, no waterfall story (milp solves in 0.4 s). Caveats: practice `milp`/`milp_markdown` stop at the 30 s `MILP_TIME_LIMIT_S` with gap 1.23 % (A-40, keep the demo laptop quiet; `outputs/demo_backup/` at freeze); `milp_markdown` is ₹487 below `milp` (A-37). Bug fixed: `discounts.lot_id` carried a float day (`B0158@D3@1.0`) whenever the arcs table had NaN rows, so lots never matched `<batch_id>@<dest_id>@<arrival_day>`; now built from the int day (KPIs unchanged).

**P2**
- [x] **U-04** · 1.0 h — Sensitivity harness (`q10`, ε vs ε/2, overship, demand ±20 %) → `sensitivity.csv`. *Done 2026-10-14: `freshroute sensitivity`; 11 rows; practice wall time 275 s (time-limited MILP solves, A-40). q10/overship values are a team assumption (`SENS_*` in config.py).*
- [x] **U-05** · 1.0 h — **Edge-case pytest scenarios**: zero vehicle capacity (`max_trips_day = 0`), an all-expired batch, a demand spike, a day with no demand rows, a single destination. None may crash; each must produce a validated plan. *Done 2026-10-14: `test_edge_cases.py`, 5 cases × 5 policies, no crash, no engine fix needed; fefo/milp/milp_markdown 0 violations; fifo/last_day_50 keep only SHELF_LIFE/WINDOW violations by design (A-31).*
- [x] **U-06** · 0.75 h — `make check` (ruff + pytest + validate demo plan) and `make demo` (**the one command** every slide number comes from). Time it. *Done 2026-10-14: `freshroute demo` / `make demo` = ladder (5 policies) + waterfall + milp_markdown validation; 77 s wall on practice s42; `make check` now validates the demo plan (practice milp_markdown, 35.6 s step). `POST /api/demo` not added (needs multi-run jobs).*
  *Note (2026-10-14, synthetic data):* `freshroute demo` (defaults `config.DEMO_SCENARIO`/`DEMO_SEED`) = `ladder.run_ladder` (fifo, fefo, milp, milp_markdown, last_day_50 run dirs + `ladder.json`/`waterfall.json`), prints the scoreboard + waterfall, exits 1 if the `milp_markdown` plan has validator violations. Sensitivity is **off by default** (`--with-sensitivity`, +~275 s, U-04). **`make demo` measured 77 s wall end to end on practice s42** (76.1 s inside the command; both MILP solves stop at the 30 s limit, A-40); numbers identical to U-03. `make check` now validates the demo plan (practice `milp_markdown` s42): that step measured 35.6 s. `POST /api/demo` not added: the job queue is per-run (`cli.run`, `run_id` → `metrics.json` state), a multi-run demo job is not trivial and the CLI is the source of every number anyway.
- [ ] **U-07** · 0.25 h — First dry run of an organizer-format scenario through the adapter.
  *Note (2026-10-14): **BLOCKED on S-01**, no dry run possible.* Checked: `backend/src/freshroute/adapters/` holds only an empty `__init__.py` (no `organizer.py`); no organizer-format fixture under `backend/tests/fixtures/`; `data/organizer/` does not exist and `data/agmarknet/` is empty. An organizer format is not invented here (rule #1); write `adapters/organizer.py` + the §8 mapping when the material lands, then run `freshroute demo --scenario <converted>`. *Unblocks with S-01.*

**P3**
- [x] **U-08** · 0.75 h — Waterfall and attribution-ladder charts (recharts, from `GET /api/ladder`). *Done 2026-10-14: recharts 3.10.1 waterfall + ladder from `GET /api/ladder`; 404 → hint to run `freshroute ladder`.*
- [x] **U-09** · 0.75 h — Dispatch sheet CSV + WhatsApp-style text + UI table (priority-ordered, slack in hours), from `GET /api/runs/{id}/dispatch-sheet`. *Done 2026-10-14: UI table (served order, ≤1 decimal), copyable text, client-side CSV download of the served records.*
- [x] **U-10** · 0.5 h — Reason-card drawer (click a shipment → card) and discount cards, from `GET /api/runs/{id}/reason-cards`. *Done 2026-10-14: drawer (chosen, runner-up, alternatives with reason codes) + discount cards; rows matched to cards by `priority_rank` + `batch_id` (dispatch rows have no `shipment_id`).*
- [x] **U-11** · 0.75 h — Shelf-life countdown map (react-leaflet over `geo.csv`, colour by hours left) with colour-coded-table fallback. *Done 2026-10-14: react-leaflet 5.0.0, no tile layer (offline); colour = min served `slack_h` per destination; table fallback when `geo.csv` is absent. On practice s42 every destination is red (each has a load with 0.2–1 h slack).* *Superseded 2026-10-14 by an offline SVG route network (D-24 amendment); Leaflet removed.*
- [x] **U-12** · 0.25 h — "Trust" tab: assumptions, coefficients, run manifest. *Done 2026-10-14: `GET /api/config` (config.py constants verbatim) + run manifest; assumptions point to ARCHITECTURE §20.*

**Gate G3 (H18):** end-to-end click-through works — press **Plan** → scoreboard → waterfall → ladder → click a batch for its reason card → dispatch sheet · `make check` green · merge and tag **`v0.1-spine`**. From here on, add-ons must not break the spine.
*If red:* cut per §9 before starting Phase 4.

**G3 result (2026-10-14):** passed. `make check` green (ruff, 168 passed + 1 xfailed, frontend build, demo plan practice/milp_markdown s42 validated with 0 violations). Pratham clicked through `make serve` live in a browser: Plan → scoreboard → waterfall → ladder → reason card → dispatch sheet, all animations working. UI restyled on Mantine + motion (D-24). Open going into Phase 4: U-02 over budget at batches+vehicles 10× (252 s; batches-only 10× now 23 s), U-07 blocked on S-01, C-06 blocked. Tagged `v0.1-spine`.

**Post-G3 polish (2026-10-14, still Phase 3, no new scope in the engine):** presenter story mode (`P` or `?story=1`; →/Space/PageDown next beat, ←/PageUp back, `S` dark stage mode, `1–5` tabs, `?` help; beats in `frontend/src/lib/story.ts`), Scoreboard beats (ladder one policy per beat, spoilage melt), Plan beats (map → sheet → rank-1 reason card), offline SVG route network replacing Leaflet, tabs kept mounted with an interruptible transition (fixes the stutter on rapid tab changes), vendor chunk split. Robustness/Replan beats come with AD-05/AD-06.

---

## 7. Phase 4 — A+ add-ons (H18–H21)

Priority order (and reverse cut order): **stress test → replan → newsvendor → narrator**. Each lands behind a flag; each must pass the validator.

**P1**
- [x] **AD-01** · 0.5 h — `events.py` pydantic schema + a sample `diff.json` **committed first** (deliver by ~H18.5 so P3 can build the Replan tab against it). *Done 2026-10-14: `events.py` (pydantic, target checks, `apply_event`), 27 tests; `diff_example.json` lot id fixed.*
- [x] **AD-02** · 2.5 h — `replan.py`: apply event, freeze `dispatch_h ≤ at_h`, residual scenario, re-solve, `diff.json`, ΔKPIs = old plan under event vs replanned. Tests: frozen shipments unchanged, validator 0 violations, time measured (< 5 s on the demo scenario). `POST /api/replan` lands with AD-06. *Done 2026-10-14: `freshroute replan`, `POST /api/replan`; measured on synthetic practice s42: 2.9-3.4 s per replan, 0 violations (frozen-only violations are `FROZEN_*` warnings, A-43). Caveat, measured: the 2 s solve cap means the replan nets less than do-nothing on delay/capacity events (-79k and -137k INR on practice) because the old plan keeps selling lots the validator rejects; with a 30 s cap it breaks even but misses 5 s (A-43).*

**P2**
- [x] **AD-03** · 2.0 h — `stress.py`: 200 seeded realizations (fallback 50, then 3 named), **paired** with the baseline, P10–P90 bands and "% of scenarios where plan beats baseline", `stress_summary.json`. Time it. *Done 2026-10-14: `freshroute stress`, `GET/POST /api/stress`; practice s42, n=200 in about 54 s; plan beats fefo on net in 100% and on spoilage in 70% of paired futures (synthetic data). Simulator now samples travel and RSL (A-42).*
- [x] **AD-04** · 1.0 h — `newsvendor.py`, `--newsvendor` flag, `demand_target` table, ablation row in the ladder output. *Done 2026-10-14: `--newsvendor` on `run`/`ladder`, `demand_target.csv`, ablation row. Measured: it LOWERS net on practice s42 (1,655,781 to 1,577,091 INR) at base-case scoring (A-45); not yet run under stress.*

**P3**
- [x] **AD-05** · 1.0 h — Fan chart + sensitivity table (Robustness tab, recharts) and `q10`/ε sliders. *Done 2026-10-14: Robustness tab (hero, 200-dot matrix, bands, sensitivity sliders); rendered from a real `GET /api/stress` run (headless screenshot). Sensitivity table shows the CLI hint until `freshroute sensitivity` has been run.*
- [x] **AD-06** · 1.25 h — Replan tab: dropdown of 5 canned events, **Apply**, diff view, ΔKPIs. *Done 2026-10-14: Replan tab + `POST /api/replan` / `GET /api/runs/{id}/replan/{event}`; the API flow was exercised live on practice (202, poll, diff, narration). The Apply click and the batch-flight animation were seen only in agent screenshots with reduced motion, not in a live browser.*
- [x] **AD-07** · 0.5 h — **Template narration** (`narrator.template_narration`) over `diff.json`/`metrics.json` — works with no LLM. *Verified on the format-example fixture `backend/tests/fixtures/diff_example.json`; real `diff.json` pending AD-01/AD-02.*
- [x] **AD-08** · 0.25 h — Deck skeleton (6–7 slides, §10 below). *Done 2026-10-14: 7-slide Claude Slides skeleton (private artifact); only measured practice numbers on the demo slide, robustness slide is placeholders.*

**Stretch (only if G4 conditions are all green)**
- [ ] **AD-09** · P1 · ≤ 1.0 h, starts only after the G4 go decision (uses P1's Phase 5 time, before H-01), **must merge by H22.5 or be dropped** — LLM event parser (function calling → pydantic → dropdown fallback) + narrator over metrics/diff JSON with the "every number must appear in the JSON" guard. Template narration remains the default.

**Gate G4 (H21):** stress bands render in the UI · replan completes in < 5 s with 0 validator violations and frozen invariants holding · `--newsvendor` produces an ablation result · go/no-go on AD-09 decided (go only if all of the above are green).
*If red:* apply the cut list (§9): fall back to precomputed named scenarios / a precomputed replan loaded instantly.

---

## 8. Phases 5–7 — Hardening, freeze, wrap-up

### Phase 5 — Hardening and dry runs (H21–H23)
- [ ] **H-01** · P1 · 1.0 h — MILP edge cases (zero capacity, all-expired batch, demand spike, infeasible balance → slack used, no crash) and replan edge cases (event after everything is dispatched; event before the first dispatch; two events in a row).
- [ ] **H-02** · P2 · 1.5 h — **10 random seeds, no crashes**; determinism re-check; 10× performance; dry run of the organizers' format/hidden-scenario flow end-to-end including the submission export.
- [ ] **H-03** · P2 · 0.5 h — Commit **`outputs/demo_backup/`** (a complete demo run) and prepare the `v1.0-freeze` tag.
- [ ] **H-04** · P3 · 0.75 h — Run the **golden-path click-through 5×** on the demo scenario via `make serve`; lock seed and scenario; confirm offline operation (Wi-Fi off, `npm ci`-built assets only).
- [ ] **H-05** · P3 · 1.25 h — Complete the deck draft and the demo script (§10).
- [ ] *(AD-09 stretch continues here until H22.5 — P1.)*

**Gate G5 — FEATURE FREEZE (H23):** no crashes on 10 random seeds · edge cases pass · determinism verified · `make check` green · `outputs/demo_backup/` committed · tag **`v1.0-freeze`**. After this: bug fixes only, each approved by a second person.

### Phase 6 — Wrap-up (H23–H24)
- [ ] **V-01** · P3 · 0.5 h — Record the **backup demo video** (local run, golden path + replan). Save it in two places (laptop + USB/another machine).
- [ ] **V-02** · P3 · 0.5 h — Finalize deck with **measured** numbers from `make demo` only.
- [ ] **V-03** · P1 · 1.0 h — README: **Assumptions** (A-xx with status), **Cost-model mapping** (§8 table), sources with verified/secondhand labels.
- [ ] **V-04** · P2 · 1.0 h — README: quickstart, the one command, reproducibility (seeds, manifest, `uv.lock`), **Results table** copied from `make demo`, test instructions.

**Gate G6 (H24):** backup video saved in two places · README complete (assumptions, mapping, quickstart, results) · every slide number traceable to `make demo` output.

### Phase 7 — Verify, rehearse, submit (H24–H26)
- [ ] **R-01** · P2 · 0.5 h — **Fresh-clone test** on a different machine: clone → `uv sync` + `npm ci` → `make setup` → `make demo`; headline numbers must match.
- [ ] **R-02** · P3 · 0.5 h — Demo-laptop setup: browser/zoom, notifications off, Wi-Fi off test, `make serve` launched on the demo URL, video queued. **Confirm Node 22+ is installed** (`npm ci` needs it at setup; the CLI and `make demo` do not).
- [ ] **R-03** · P1 · 0.5 h — Q&A drill (§11) — everyone answers every question once.
- [ ] **R-04** · all · 1.0 h — **Rehearse the pitch 3× with a timer; each run under 3:00.** After each run, one minute of feedback.
- [ ] **R-05** · all · 0.5 h — Submission checklist (§13). **Last 30 minutes: no code changes.**

**Gate G7 (H26):** submitted · fresh-clone test passed · three timed rehearsals under 3:00.

---

## 9. If we fall behind — cut list

Cut from the top; **never** cut the "never" list.

1. AD-09 LLM narrator / natural-language box (keep template narration + 5-event dropdown).
2. Leaflet map (→ colour-coded table).
3. Newsvendor (AD-04).
4. Sensitivity beyond `q10` slider and ε vs ε/2.
5. Live replan (→ precomputed scenario loaded instantly, per research fallback).
6. Monte Carlo 200 → 50 → 3 named scenarios (optimistic / base / stress).
7. Reason-card polish (→ static top-3 reasons table).

**Never cut:** independent validator · cost model/metrics · simulator · feasibility pre-filter + MILP · scoreboard · attribution ladder (it kills the "strawman baseline" critique) · README assumptions · the one reproducible command · backup video.

---

## 10. Pitch and demo checklist

**Rule:** say measured numbers, never projected ones. Label synthetic data as synthetic. Only say a scale ("60 batches, 7 destinations, 4 trucks") if the demo scenario really has it.

**Framing facts (status in brackets):**
- NABCONS/MoFPI study, reference years 2020–22, 54 commodities, 15 agro-climatic zones, 292 districts; reported losses 6.02–15.05 % (fruits), 4.87–11.61 % (vegetables) [verified against PIB text].
- Tomato 8.37 % at farm stage + 3.25 % at market stage; onion 5.31 % + 1.96 % [verified]. "Market level" covers godowns, wholesalers, retailers, processing units and transport — the slice a distributor can move.
- Tomato loss value ₹5,921.15 crore [**verified (PRE-03)**: PIB release 2081044, Lok Sabha written reply, 5 Dec 2024, Annexure "Estimated Post-harvest monetary loss (Rs. in Crore)", NABCONS study, reference year 2020–22. The release does **not** say it is annual and gives **no stage split**: say "post-harvest loss valued at about ₹5,921 crore (NABCONS, 2020–22)", never "a year" or "at market stage"].
- India: 8,815 cold storages, 402.18 lakh MT capacity as of 30 June 2025 [**verified (PRE-03)**: PIB backgrounder "From Harvest to Home", Sep 2025, https://static.pib.gov.in/WriteReadData/specificdocs/documents/2025/sep/doc2025928649201.pdf]. Framing: India built storage but not a *chain* — first-mile, reefers, traceability lag.

**Corrected hook (use this, not the research draft's wording):**
> "India's government-commissioned NABCONS study found that tomatoes lose about 8.4 % at the farm stage and a further 3.25 % at the market stage — godowns, wholesalers, retailers and transport. Post-harvest loss for tomato overall is valued at roughly ₹5,921 crore in that study *[verified, PIB 2081044; the source does not say annual, so never say "a year"]*. The market-stage slice is the part a distributor can actually move."
Do **not** attach the ₹5,921 crore to the market-stage slice alone (it is the figure for tomato's post-harvest loss value, not the value of the 3.25 % slice); do **not** say "3.25 % of that loss" (3.25 % is a share of tomato *output*, not of the loss); and do not say "a year" unless the source confirms the ₹ figure is annual.

**3-minute script (timings from the research):**

| Time | Beat | Notes |
|---|---|---|
| 0:00–0:20 | Hook | Corrected hook above |
| 0:20–0:35 | User and moment | "5 a.m. at a hub; N batches, M destinations, K trucks; 20 minutes to decide" — real counts only |
| 0:35–1:30 | **Live demo, golden path** | Load scenario → **Plan** (say the measured seconds) → scoreboard lights up → click a batch: reason card ("sent to Pune, not Delhi: Delhi leaves 9 h of life, below the 24 h sell window…" — use the real numbers from the card) → click the discount card |
| 1:30–2:05 | Robustness | Press a canned disruption (e.g. +6 h delay on lanes to one destination) → diff (moved batches, deepened markdowns, ΔKPIs, **measured** replan time) → fan chart: "across 200 sampled futures we beat baseline in X %" (X from `stress_summary.json`) |
| 2:05–2:25 | Trust | Zero violations by the independent validator; one seeded command; assumptions in the README |
| 2:25–3:00 | Commercial | SaaS per hub per month for distributors, FPO aggregators and cold-storage operators. Positioning: "Afresh decides what a store orders. Wasteless decides the shelf price. Celcius books the reefer. **FreshRoute decides which batch goes where, when, and at what markdown, at the distributor hub.**" Next: pilot with one FPO using Agmarknet prices |

Competitor claims, if cited, are **vendor-reported and unaudited**: Afresh (US; $34M raise April 2026; "up to 25 % shrink reduction"), Wasteless (expiry-anchored shelf markdowns; "40 % waste reduction at Edeka Hamburg"). Celcius Logistics (India): ₹250 crore Series B, May 2025.
*PRE-03 status (2026-10-14):* Afresh $34M, 21 Apr 2026, "up to 25 % shrink reduction" [verified as **company-reported**: PR Newswire release, https://www.prnewswire.com/news-releases/afresh-raises-34m-to-scale-ai-across-the-grocery-industry--driving-fresher-food-stronger-margins-and-less-waste-302747794.html]. Celcius ₹250 crore Series B, announced 6 May 2025, equity + debt (+ secondary), led by Eurazeo and Omnivore [verified in trade press: https://india.entrepreneur.com/en-in/news-and-trends/celcius-logistics-secures-inr-250-cr-in-series-b-to-expand/491145; say "raised ₹250 crore", not "₹250 crore equity"]. Wasteless "40 % at Edeka Hamburg" [**secondhand only**: Solar Impulse listing; Wasteless's own case study is Edeka Rhein-Ruhr fresh meat, 47–74 % within the covered assortment, https://wasteless.com/success/edeka-achieves-dramatic-waste-reduction-and-margin-gains-with-wasteless-ai-powered-markdowns. **Recommend dropping the number**; say "expiry-based shelf markdowns" only]. Skip Ninjacart's tonnage — the figure is dated (~2019).

**Demo hygiene**
- [ ] Start with `make serve` before walking on stage; the browser is already on the URL. Nothing calls the internet.
- [ ] Run live from local data; backup video queued; `outputs/demo_backup/` ready.
- [ ] Keep the demo to one golden path; no live debugging on stage.
- [ ] Value must be clear within ~30 seconds; a simple demo the judges understand beats a clever one they can't.

---

## 11. Q&A prep — everyone answers each

Spoken answers with measured numbers: `docs/QA.md`.

1. **"Why trust your elasticity?"** — It's a disclosed assumption (A-11), uplift is capped, and the sensitivity table shows results at ε and ε/2.
2. **"What if the hidden data is 10× larger?"** — The feasibility pre-filter shrinks the model; 30 s limit returns the incumbent; aggregation fallback; quote the **measured** U-02 numbers.
3. **"How does this reach a real distributor?"** — SaaS per hub; pilot with one FPO/aggregator; Agmarknet prices; dispatch sheet works over WhatsApp.
4. **"Is your baseline fair?"** — The organizers' baseline is the official comparison; the attribution ladder also beats FEFO, not just FIFO (research cites a simulation where FEFO cut expired product 50 % vs FIFO — secondhand).
5. **"What does the LLM actually decide?"** — Nothing. It translates a sentence to a validated event and narrates numbers it was given; HiGHS decides. (If AD-09 was cut: "We don't use an LLM for decisions; narration is template-based.")
6. **"How do you know the plan is feasible?"** — An independent validator that doesn't import optimizer code; infeasible arcs never exist in the model.
7. **"What if constraints can't all be met?"** — Soft constraints with penalty slacks; slack usage is reported; fallback plan if the solver times out.
8. **"Is this real data?"** — Say plainly: synthetic (or organizer-provided) data, calibrated for plausibility against NABCONS market-stage loss figures and Agmarknet prices; post-harvest-loss statistics are context, not model inputs.

---

## 12. Rubric coverage checklist (tick when the evidence exists)

| Rubric (pts) | Evidence we can show | Task |
|---|---|---|
| Spoilage reduction (20) | Spoilage kg/% baseline → plan; spoilage breakdown; ladder | C-07, C-12 |
| Demand fulfillment (15) | Fulfillment % and **min destination fill** | C-12 |
| Net economic outcome (20) | Net ₹ + reconciling waterfall | C-07, U-08 |
| Allocation feasibility (15) | Independent validator: baseline n vs ours **0** | F-04, C-12 |
| Robustness & sensitivity (10) | MC bands, % scenarios beating baseline, `q10`/ε sensitivity, replan | AD-03, U-04, AD-02 |
| Engineering & reproducibility (10) | One seeded command, tests, manifest, locked deps (`uv.lock` + `package-lock.json`), fresh-clone pass | U-06, C-08, R-01 |
| Explainability & commercial (10) | Reason cards, dispatch sheet, positioning slide | U-01, U-09, V-02 |

---

## 13. Submission checklist (R-05)

- [ ] Repo state = `v1.0-freeze` (+ approved fixes only); `make check` green.
- [ ] Plan export in the organizers' required format validated (our validator + their checker if provided).
- [ ] README: assumptions, cost-model mapping, quickstart, results, sources (verified vs secondhand labelled).
- [ ] Deck exported; backup video playable from two places; `outputs/demo_backup/` present.
- [ ] No secrets or restricted organizer data in git; `.env` ignored.
- [ ] Demo laptop: charged, Wi-Fi-off run tested, `make serve` pre-launched on the demo URL, Node 22+ installed.
- [ ] Everyone knows who presents which beat and who handles Q&A.
