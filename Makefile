# Commands below can be run by hand if make is missing (Windows): copy the recipe lines.
PY ?= python
export PYTHONPATH := src

setup:
	$(PY) -m pip install -r requirements.txt
	$(PY) -m pip install -e . --no-deps

test:
	$(PY) -m pytest -q

# ruff + pytest (+ validate demo plan once F-04 lands)
check:
	$(PY) -m ruff check .
	$(PY) -m pytest -q
	$(PY) -m freshroute.cli run --scenario tests/fixtures/tiny_3batch --policy milp --out outputs/check_milp --fail-on-violations

demo:
	@echo "demo: not implemented yet (freshroute demo lands with the spine)"

app:
	$(PY) -m streamlit run app/streamlit_app.py

run-stub:
	$(PY) -m freshroute.cli run --scenario tests/fixtures/tiny_3batch --policy milp --seed 42

.PHONY: setup test check demo app run-stub
