# Commands below can be run by hand if make is missing (Windows): copy the recipe lines.
# uv owns Python (D-15): `uv sync` installs, `uv run` executes.

setup:
	uv sync

test:
	uv run pytest -q

# ruff + pytest + validate the demo plan
check:
	uv run ruff check .
	uv run pytest -q
	uv run freshroute run --scenario backend/tests/fixtures/tiny_3batch --policy milp --out outputs/check_milp --fail-on-violations

demo:
	@echo "demo: not implemented yet (freshroute demo lands with the spine)"

run-stub:
	uv run freshroute run --scenario backend/tests/fixtures/tiny_3batch --policy milp --seed 42

.PHONY: setup test check demo run-stub
