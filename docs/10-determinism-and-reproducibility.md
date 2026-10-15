# 10 · Determinism and reproducibility

Ten rubric points reward repeatable runs and correct calculations, and every other score depends on being believed. This guide explains how identical inputs give identical outputs, and the one place where that guarantee has a ceiling. Reference: `ARCHITECTURE.md` §18.

## The promise

Same scenario, same seed, same flags ⇒ byte-identical `metrics.json`. The fields excluded from that promise are the timestamp and `solve_seconds`, which are about the run, not the result.

## How we keep it

- **Seeded randomness only.** Use `numpy.random.default_rng(seed)`. Never the global `random` or `np.random.*`. The seed is part of the run id, for example `practice__milp_markdown__s42`.
- **Sort before you iterate.** Dataframe and dict order changes results through tie-breaking. Batches and arcs are sorted with stable keys, and indexes are reset.
- **Fixed solver settings.** Time limit, gap and tie-break term are constants in `config.py`.
- **Pinned dependencies.** `uv.lock` and `package-lock.json` are committed and never edited by hand. Python is pinned to 3.13 (D-22), partly because `pulp 4.0.0` needs 3.12 or newer.
- **A manifest for every run.** `run_manifest.json` records the git SHA, seed, flags, scenario path and the SHA-256 of its CSV bytes, package versions, solver status, gap, slack usage, and whether the fallback ran.

## The tests that guard it

- `backend/tests/test_determinism.py` runs twice and compares output.
- `backend/tests/test_golden.py` compares output hashes against `backend/tests/golden/hashes.json`. Line endings are normalised first so Windows and Unix agree. If a deliberate change shifts outputs, regenerate the hashes and say why in the commit message.

## The honest ceiling

The solver limit is **wall-clock** time (30 s). On the demo scenario the solver reaches that limit, so a slower or busier machine can stop at a different incumbent and return a different plan (A-40). Determinism is exact for solves that finish below the limit and approximate otherwise.

What to do about it:

- Never quote a number from a laptop that was running something heavy.
- Quote numbers from a stated run (`scenario`, `seed`, commit), and use the copies in `outputs/demo_backup/`.
- If asked, say exactly this: the model and simulator are deterministic; the time-limited MILP incumbent can vary slightly across hardware.

## Fresh-clone check

On a clean directory or machine: `make setup && make demo`, then compare the headline numbers with the README results. Node 22 or newer is needed for `npm ci`. Do this before submitting (see `SUBMISSION.md`).

## Gotchas

- Anything under `outputs/` is regenerated and gitignored, except `outputs/demo_backup/`.
- Windows line endings can change file hashes. Compare through the golden tests, not by `diff` alone.
- Each git worktree needs its own `uv sync` and `npm ci`, because `.venv` and `node_modules` are not committed.
