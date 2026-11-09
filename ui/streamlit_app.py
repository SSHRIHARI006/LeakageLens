from pathlib import Path
import tempfile
import pandas as pd
import plotly.express as px
import streamlit as st
from leakagelens import AuditConfig, LeakageLens
from leakagelens.ingestion import load_table
from leakagelens.reporting import markdown_report

st.set_page_config(page_title="LeakageLens", page_icon="🔎", layout="wide")
st.title("LeakageLens")
st.caption("Evidence-based leakage diagnostics for tabular machine learning. Findings are risks, not proof.")
uploaded = st.file_uploader("Upload CSV, XLSX, or Parquet", type=["csv", "xlsx", "xls", "parquet"])
if uploaded:
    suffix = Path(uploaded.name).suffix
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as handle:
        handle.write(uploaded.getvalue()); uploaded_path = handle.name
    try:
        frame = load_table(uploaded_path)
        st.dataframe(frame.head(), use_container_width=True)
        cols = frame.columns.tolist()
        target = st.selectbox("Target column", cols)
        task = st.selectbox("Task", ["classification", "regression"])
        group = st.selectbox("Group/entity column (optional)", [""] + cols)
        time = st.selectbox("Time column (optional)", [""] + cols)
        context = st.radio("Inference scenario", ["iid", "temporal"], horizontal=True)
        if st.button("Run Leakage Audit", type="primary"):
            config = AuditConfig(target=target, task=task, group_column=group or None, time_column=time or None, inference_context=context)
            result = LeakageLens(config).audit(frame)
            a, b, c = st.columns(3); a.metric("Risk score", f"{result.risk_score}/100"); b.metric("Risk level", result.risk_level); c.metric("Findings", len(result.findings))
            st.plotly_chart(px.bar(x=list(result.signal_scores.keys()), y=list(result.signal_scores.values()), labels={"x":"Signal", "y":"Score"}, title="Leakage signals"), use_container_width=True)
            st.subheader("Findings")
            st.dataframe(pd.DataFrame([f.to_dict() for f in result.findings]), use_container_width=True)
            if result.inflation:
                st.subheader("Original versus safer evaluation")
                st.dataframe(pd.DataFrame(result.inflation).T, use_container_width=True)
            st.download_button("Download Markdown report", markdown_report(result), file_name="leakagelens_report.md", mime="text/markdown")
    finally:
        Path(uploaded_path).unlink(missing_ok=True)
else:
    st.info("Try the generated examples in `data/` after running `python examples/generate_datasets.py`.")
