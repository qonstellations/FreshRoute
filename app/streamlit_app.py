"""FreshRoute dashboard (ARCHITECTURE §16). Reads outputs only via data_access; never computes
a KPI (deltas below are display arithmetic on two numbers read from disk)."""
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
import data_access  # noqa: E402

st.set_page_config(page_title="FreshRoute", layout="wide")
st.title("FreshRoute")
st.warning("SYNTHETIC DATA: figures come from synthetic scenarios or a hand-written example.")

runs = data_access.list_runs()
run_id = st.sidebar.selectbox("Run", runs) if runs else None
m, is_fixture = data_access.load_metrics(run_id)
if is_fixture:
    run_id = None
    st.info("No run under outputs/. Showing tests/fixtures/metrics_example.json (placeholder).")

manifest = data_access.load_manifest(run_id)
if manifest and (manifest.get("solver") or {}).get("fallback_used"):
    st.error("Solver fallback used: this plan came from the FEFO-greedy fallback, not HiGHS.")

validation = data_access.load_validation(run_id)
base = None if is_fixture else data_access.load_baseline(m["scenario"], m["seed"])
k = m["kpis"]
bk = base["kpis"] if base else None


def _delta(key: str, fmt: str) -> str | None:
    return None if bk is None else fmt.format(k[key] - bk[key])


c = st.columns(4)
c[0].metric("Spoilage", f"{k['spoilage_kg']:,.0f} kg ({k['spoilage_pct']:.1f}%)",
            _delta("spoilage_kg", "{:+,.0f} kg"), delta_color="inverse")
c[1].metric("Demand fulfillment", f"{k['demand_fulfillment_pct']:.1f}%",
            _delta("demand_fulfillment_pct", "{:+.1f} pp"))
c[2].metric("Net", f"₹{k['net_inr']:,.0f}", _delta("net_inr", "{:+,.0f} ₹"))
c[3].metric("Violations",
            f"baseline {bk['violations']} vs ours {k['violations']}" if bk else k["violations"])
st.caption(
    f"run {m['run_id']} · scenario {m['scenario']} · policy {m['policy']} · seed {m['seed']}"
    + (f" · deltas vs {base['policy']} ({base['source']})" if base else " · no baseline on disk")
)

names = ["Scoreboard", "Plan", "Robustness", "Replan", "Trust"]
tabs = st.tabs(names)
with tabs[0]:
    st.metric("Min destination fill", f"{k['min_dest_fill_pct']:.1f}%",
              _delta("min_dest_fill_pct", "{:+.1f} pp"))
    st.subheader("Independent validator")
    if validation is None:
        st.write("No validation.json for this run.")
    else:
        st.metric("Violation total", validation["violation_total"])
        counts = validation.get("counts") or {}
        if counts:
            st.table(pd.DataFrame(sorted(counts.items()), columns=["code", "count"]))
        warnings = validation.get("warnings") or []
        if warnings:
            st.write("Warnings")
            st.table(pd.DataFrame(warnings))
for tab, name in zip(tabs[1:], names[1:], strict=True):
    tab.write(f"{name}: coming in a later task.")
