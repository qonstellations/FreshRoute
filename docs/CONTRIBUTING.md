# CONTRIBUTING.md

**FreshRoute — how we work together** (team of 3 · ~20 hours · Plan A+)

> Read this once at PRE-05, then keep it open. Companion docs: `ARCHITECTURE.md` (how the system works) · `DATABASE.md` (data contracts) · `TODO.md` (schedule and gates).

---

## 1. The project in one paragraph

FreshRoute is a hub-level decision tool for perishable produce: given batches with remaining shelf life, destinations with demand and delivery windows, and vehicles with capacities, it decides **which batch goes where, when, and at what markdown**. The spine is an explainable MILP (HiGHS) over a pre-filtered set of shelf-life-feasible arcs, scored by one seeded simulator against the organizers' cost model and checked by an independent validator. A+ adds a Monte Carlo stress test, an event-driven replan, and a newsvendor demand target. We win by being **correct, reproducible and easy to understand in 3 minutes** — not by being the fanciest.

---

## 2. Team and ownership

| Role | Person | Owns (primary) | Reviews PRs from |
|---|---|---|---|
| **P1 — Optimization lead** | ____________ | `shelflife.py`, `feasibility.py`, `policies/milp.py`, `events.py`, `replan.py`, reason-card fields | **P3** |
| **P2 — Simulation, metrics & validation** | ____________ | `cli.py`, `config.py`, `schema.py`, `io.py`, `costmodel.py`, `simulator.py`, `metrics.py`, `ladder.py`, `stress.py`, `newsvendor.py`, baselines, `validator/`, `Makefile`, tests infrastructure | **P1** |
| **P3 — Product, UI & AI/pitch** | ____________ | `generator.py`, `adapters/organizer.py`, `discount.py`, `dispatch_sheet.py`, `narrator.py`, `app/`, README (P3 coordinates; P1 writes assumptions + cost-model mapping, P2 writes quickstart + results — V-03/V-04), deck, demo script, video | **P2** |

Full module-by-module ownership: `ARCHITECTURE.md` §6. Review rotation is circular (P2 reviews P1, P3 reviews P2, P1 reviews P3) so nobody merges unreviewed and everyone sees the interfaces.

**Touching someone else's module:** allowed, but (a) tell the owner in chat first, (b) keep the change small, (c) the owner reviews it. Shared files (`config.py`, `schema.py`, `Makefile`) — make small PRs and merge them fast.

---

## 3. Ground rules (the non-negotiables)

1. **The organizers' cost model and data format override ours.** Coefficients live only in `costmodel.py`, `config.py` or the dataset — never as literals elsewhere.
2. **Validator independence.** `validator/` may import only stdlib, pandas, numpy, `freshroute.schema`, `freshroute.io`. It re-implements the maths; it never imports `shelflife.py`, `feasibility.py`, `costmodel.py`, policies, `simulator.py`, or `discount.py`. A test enforces this.
3. **One simulator scores every policy.** No policy computes its own "net ₹" for reporting.
4. **Determinism.** Same scenario + seed + flags ⇒ identical `metrics.json`. All randomness through `numpy.random.default_rng(seed)`; never the global `random`/`np.random` state.
5. **The LLM never decides.** It may translate a sentence into a pydantic-validated event and narrate JSON it was given. Everything else is HiGHS and code.
6. **Add-ons are flags.** `--newsvendor`, `--no-markdown`, stress and replan must be removable without breaking the spine.
7. **Never crash on a scenario.** Soft constraints, solve time limit, FEFO-greedy fallback.
8. **Measured numbers only** on slides and in the README. Synthetic data is always labelled synthetic.
9. **The demo is offline.** No live API, no network dependency, backup video ready.
10. **Feature freeze at H17.** After that: bug fixes only, each approved by a second person.
11. **`main` is always green.** `make check` before every push to a PR branch; never merge a red PR.

---

## 4. Setup

```bash
git clone <repo-url> freshroute && cd freshroute
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt      # use the venv; no --break-system-packages needed inside it
make setup                           # installs the package in editable mode, runs a smoke test
make test                            # fast unit tests (aim: well under a minute)
make run-stub                        # freshroute run --scenario tests/fixtures/tiny_3batch --policy milp --seed 42
make app                             # Streamlit dashboard
make check                           # ruff + pytest + validate the demo plan  (run before every push)
make demo                            # THE one command all slide numbers come from
```

No `make` (e.g. plain Windows)? Run the commands written in the comments at the top of the `Makefile`.

Core dependencies: `pandas`, `numpy`, `scipy>=1.9`, `pulp`, `highspy`, `pydantic>=2`, `streamlit`, `pydeck`, `plotly`, `pytest`, `ruff`. Optional: an LLM client (only for the AD-09 stretch). `statsforecast` is **not** used in this build.

Environment variables (never committed): `LLM_API_KEY` (and provider name) if AD-09 is attempted. Put them in `.env`, which is git-ignored.

---

## 5. Git workflow

**Trunk-based, short-lived branches, squash merges.**

- **Branches:** `p1/feat-milp-objective`, `p2/fix-validator-window`, `p3/ui-waterfall` — `<person>/<type>-<topic>`.
- **Commits** (conventional): `type(scope): summary (TASK-ID)`
  - types: `feat fix test docs chore refactor perf`
  - scopes: `gen sim metrics validator milp feas discount stress replan newsvendor ui narrator cli io cost docs`
  - example: `feat(milp): add unshipped-expiry penalty (C-01)`
- **Pull requests:** keep them small (aim under ~300 changed lines; one task ID per PR). Title starts with the task ID. Reviewer responds within ~10 minutes; if the reviewer is unavailable for 10 minutes, pair-review on a call and merge — don't let PRs wait.
- **Before opening:** rebase on `main`, run `make check`, update docs if a contract changed (§7).
- **Merging:** squash-merge once approved and green. The author merges.
- **Tags:** `v0.1-spine` at G3 (H12) · `v1.0-freeze` at G5 (H17).
- **After the freeze:** only bug-fix PRs, prefixed `fix(...)`, approved by a second person, with a test where practical. If the fix touches the demo path, re-run the golden-path click-through.
- **Never commit:** `.env`, API keys, `.venv`, `outputs/` (except `outputs/demo_backup/` at the freeze), large binaries, or organizer data the rules don't allow us to redistribute (`data/organizer/` is git-ignored by default — confirm the rule at S-01 before changing that).

PR description template:

```
Task: <ID>   Owner: <P1/P2/P3>
What changed:
How I tested (commands + result):
Contract changes? (DATABASE.md / metrics.json / CLI / event schema)  yes/no — link
Cost-model or assumption changes? (ARCHITECTURE §7 / §20)           yes/no — link
Checklist: [ ] make check green  [ ] tests added/updated  [ ] no new magic numbers
           [ ] docs updated  [ ] validator independence kept  [ ] deterministic
```

Review checklist: does it match the contract? does a test prove it? any literal coefficients? any unseeded randomness? does it keep the validator independent? does it still run with the add-on flags off?

---

## 6. Code standards

- Python **3.10+** (one pinned version in `.python-version`). Format and lint with **ruff**; type hints on all public functions.
- **Units in names and docstrings:** `_kg`, `_h`, `_inr`, `_inr_kg`, `_c`, `_pct` (0–100), `_frac` (0–1). Percent → fraction conversion happens **only** in `io.py` (D-06).
- **Column names** come from constants in `schema.py`; no stringly-typed column names scattered around.
- **No magic numbers:** tunables in `config.py`, coefficients from the dataset. Every default in `config.py` has a comment saying whether it comes from the research doc or is a team assumption.
- **Pure functions** where possible (`discount.build_discounts`, `feasibility.build_arcs`, `shelflife.*`); side effects (file writes) only in `cli.py`/`io.py`/runners.
- **Deterministic ordering:** sort DataFrames by explicit keys before iterating, break ties by ID. If the determinism test (C-08) fails on the MILP, pin solver threads and any solver seed option.
- **Float tolerance:** compare with `FLOAT_TOL` from `config.py` (default 1e-6), never `==` on floats.
- **Logging, not print,** in library code. Warnings from data loading are counted and shown (`DATABASE.md` §7).
- **Errors:** fail loudly on bad input at load time; **never** swallow exceptions in the pipeline. Solver trouble is handled by the documented fallbacks (`ARCHITECTURE.md` §9.5), and fallbacks are recorded in the manifest and shown in the UI.
- **UI rule:** `app/` only reads `outputs/` (via `data_access.py`) and calls CLI functions; it never computes a KPI.
- **Docs in code:** each module starts with a 3–5 line docstring naming the section of `ARCHITECTURE.md` it implements.

---

## 7. Contracts and the change process

**Contracts** = anything another person's code or the UI depends on:
- table/column definitions and file formats (`DATABASE.md`)
- `metrics.json`, `plan.csv`, `validation.json`, `reason_cards.json`, `diff.json`, event schema
- CLI commands/flags and `make` targets
- function signatures listed in `ARCHITECTURE.md` §6

**To change a contract:**
1. Update the relevant document **in the same PR** as the code.
2. Post `CONTRACT: <what changed, who is affected>` in the team chat before merging.
3. Bump `schema_version` if a file/JSON format changed, and update `tests/fixtures/metrics_example.json` so the UI keeps working.
4. The affected owner approves the PR.

**IDs:** `A-xx` = assumption, `D-xx` = decision, `AD-xx` = A+ add-on task; other task prefixes are in the `TODO.md` ID legend.

**Assumptions and decisions:** a new modelling assumption goes in `ARCHITECTURE.md` §20 (next free `A-xx`); a design decision goes in `DECISIONS.md` (next free `D-xx`). If the organizers' documents contradict an assumption, update the row and the code — theirs wins.

---

## 8. Testing

`make test` must stay fast. Required tests (each maps to a task in `TODO.md`):

| Area | Test |
|---|---|
| Shelf life | Worked example: usable life 87 / 69 / 13 h; the third arc is rejected (F-01) |
| Feasibility | One test per `reject_reason`; absolute and daily window modes; rail slot alignment (F-02) |
| Units | `*_pct` in file → fraction in memory → same `*_pct` in outputs (D-06) |
| Cost model / metrics | Hand-computed `tiny_3batch` fixture; all `metrics.json` invariants — revenue/discount identity, net identity, spoilage breakdown sum, **mass balance** `supply = sold + spoilage + carry-over` (F-04, F-05) |
| Validator | Inject one violation per hard code → exactly that code appears; AST test forbids imports of optimizer code; randomized agreement with `shelflife.py` (F-04) |
| Simulator | Fixture result matches the hand computation; FEFO sales order; handling loss; expiry; carry-over (F-06) |
| Discount rule | Tier boundaries (risk 0.09 / 0.10 / 0.29 / 0.30 / 0.50 / 0.51 → 0 / 10 / 10 / 20 / 20 / 35 %, A-22), 24 h trigger, caps, salvage floor, worth-it test, monotonicity (F-09) |
| MILP | Beats FEFO on 3 seeds (G2); **consistency with simulator** (C-04); respects capacity/trips; slack/fallback paths (C-02) |
| Waterfall | `baseline + Σ deltas = plan` within ₹0.01 (C-07) |
| Determinism | Run twice → identical `metrics.json` (C-08) |
| Stress | Paired scenarios reproducible from the seed; band ordering P10 ≤ P50 ≤ P90 (AD-03) |
| Replan | Frozen shipments unchanged; validator 0 violations; time recorded (AD-02) |
| Newsvendor | Critical-ratio value, clamp, `c_u ≤ 0` ⇒ target 0 (AD-04) |
| Edge cases | Zero capacity, all-expired batch, demand spike, missing demand day, single destination — no crash, validated plan (U-05) |
| Narrator | Guard rejects a narration containing a number not in the JSON (AD-09) |

Bug found? Write the failing test first when it takes less than five minutes.

---

## 9. Data, secrets, sources

- **Organizer data:** do not publish or redistribute beyond what the rules allow; confirm at S-01. `data/organizer/` is git-ignored by default.
- **Secrets:** API keys only in environment variables / `.env` (git-ignored). If a key is ever committed, rotate it immediately and tell the team.
- **Synthetic data:** generated by `freshroute generate --seed …`; always flagged `source: synthetic` in `scenario.json` and on the scoreboard.
- **Real-world facts** (post-harvest losses, e-NAM, cold storage, competitors) are **context, not model inputs.** In the README and deck, label each as *verified against official source*, *secondhand*, or *vendor-reported/unaudited* (status lists are in `TODO.md` §10). Don't paste long passages from sources; paraphrase and cite.
- **Agmarknet:** use the cached snapshot (`data/agmarknet/`). Never call the live API in the demo.
- **AI assistants / external services:** follow the event's rules (open question 7 in `TODO.md`). Whatever generates code, a human owner reviews and understands it before merge.

---

## 10. Communication and rituals

- **One chat channel.** Prefixes: `CONTRACT:` (interface change), `BLOCKED:` (waiting on someone/something), `FYI:` (no action needed), `GATE:` (checkpoint result).
- **Gate checkpoints** (≈10 minutes, everyone, at H2, H5, H9, H12, H15, H17, H18, H20): what's green, what's red, cut or continue (`TODO.md` §9 cut list). Update the checkboxes in `TODO.md` right then.
- **Blocked for 15 minutes?** Say so in chat. Stuck for 45 minutes? Pair up.
- **Decisions** are written down (`DECISIONS.md`), not remembered.
- **Handoffs:** when you finish something others depend on (generator v0, `diff.json` sample, `metrics.json` fields), announce it in chat with the path.
- **Wellbeing:** one meal break around H8–H9, a short break roughly every 4 hours. Tired people introduce bugs; the freeze and rehearsal buffers exist so nobody needs to push through the last hour.

---

## 11. Demo hygiene (from H12 onward)

- Every slide number comes from `make demo` on the frozen tag — never from a one-off run.
- Rehearse on the demo laptop with Wi-Fi off. Keep `outputs/demo_backup/` and the video (in two places) ready.
- The golden path is fixed: **Plan → scoreboard → one reason card → one discount card → one canned disruption → stress bands.** No live debugging on stage; if something breaks, switch to the video.
- Say only what was measured (plan time, replan time, % of futures where we beat the baseline).

---

## 12. Definition of done

**A task is done when:** code merged to `main` via an approved PR · tests added/updated and `make check` green · docs/contracts updated · task checkbox ticked in `TODO.md` · any dependent teammate told.

**A phase is done when:** its gate criteria in `TODO.md` are met and the checkpoint was held.

**The project is done when:** G7 passes — submitted, fresh-clone test passed, three timed rehearsals under 3:00.

---

## 13. When things go wrong

- **Behind schedule →** apply the cut list in `TODO.md` §9 at the next gate. Protect the spine; never cut the validator, simulator, MILP, scoreboard, attribution ladder, README assumptions, the one command, or the backup video.
- **MILP doesn't beat FEFO →** compare objective coefficients to the simulator (C-04) before tuning anything.
- **Organizer cost model differs →** change `costmodel.py`/`config.py`/adapter only; update `ARCHITECTURE.md` §7 and §20 in the same PR.
- **Solver slow or failing →** time limit + incumbent + FEFO fallback + aggregation (`ARCHITECTURE.md` §9.5); record it in the manifest.
- **Merge conflict in a shared file →** the person who merged second resolves it, and tells the other.
- **Disagreement on an approach →** timebox to 5 minutes; the module owner decides; log it in `DECISIONS.md` if it matters.
