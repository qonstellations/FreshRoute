# Commands below can be run by hand if make is missing (Windows): copy the recipe lines.
# uv owns Python (D-15); npm owns frontend/ (D-19). Node 22+ required.

setup:
	uv sync
	npm ci --prefix frontend

test:
	uv run pytest -q

# ruff + pytest + frontend type-check/build + validate the demo plan
check:
	uv run ruff check .
	uv run pytest -q
	npm --prefix frontend run build
	uv run freshroute run --scenario backend/tests/fixtures/tiny_3batch --policy milp --out outputs/check_milp --fail-on-violations

demo:
	@echo "demo: not implemented yet (freshroute demo lands with U-06)"

# dev: API with reload on :8000; run `make web` alongside for Vite on :5173 (proxies /api)
api:
	uv run uvicorn freshroute.api.app:app --reload --host 127.0.0.1 --port 8000

web:
	npm --prefix frontend run dev

# demo: one URL, FastAPI serves frontend/dist (D-20)
serve:
	npm --prefix frontend run build
	uv run uvicorn freshroute.api.app:app --host 127.0.0.1 --port 8000

run-stub:
	uv run freshroute run --scenario backend/tests/fixtures/tiny_3batch --policy milp --seed 42

.PHONY: setup test check demo api web serve run-stub
