"""FreshRoute dashboard shell (ARCHITECTURE §16). Reads outputs only via data_access."""
import sys
from pathlib import Path

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
    st.info("No run under outputs/. Showing tests/fixtures/metrics_example.json (placeholder).")

k = m["kpis"]
c = st.columns(4)
c[0].metric(
    "Spoilage", f"{k['spoilage_kg']:,.0f} kg", f"{k['spoilage_pct']:.1f}%", delta_color="off"
)
c[1].metric("Demand fulfillment", f"{k['demand_fulfillment_pct']:.1f}%")
c[2].metric("Net", f"₹{k['net_inr']:,.0f}")
c[3].metric("Violations", k["violations"])
st.caption(
    f"run {m['run_id']} · scenario {m['scenario']} · policy {m['policy']} · seed {m['seed']}"
)

names = ["Scoreboard", "Plan", "Robustness", "Replan", "Trust"]
for tab, name in zip(st.tabs(names), names, strict=True):
    tab.write(f"{name}: coming in a later task.")
