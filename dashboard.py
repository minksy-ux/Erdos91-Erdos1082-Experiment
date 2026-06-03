#!/usr/bin/env python3
"""Streamlit dashboard for experiment tracking and certification inspection."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import plotly.express as px
import streamlit as st

from utils.database import ExperimentDB

st.set_page_config(page_title="Erdos Rigidity Explorer", layout="wide")
st.title("Erdos #91 and #1082 Explorer")

db_path = st.sidebar.text_input("SQLite DB path", value="results/erdos_experiments.db")
limit = st.sidebar.slider("Rows", min_value=10, max_value=300, value=60, step=10)
n_filter = st.sidebar.number_input("Filter by n (0 = all)", min_value=0, max_value=200, value=0)

db = ExperimentDB(db_path=db_path)
rows = db.get_best(n=(None if n_filter == 0 else int(n_filter)), limit=int(limit))
benchmark_rows = db.get_benchmark_summaries(n=(None if n_filter == 0 else int(n_filter)), limit=30)
family_rows = db.get_latest_family_evidence(n=(None if n_filter == 0 else int(n_filter)), limit=20)

tab_best, tab_chart, tab_bench, tab_fam, tab_cert = st.tabs(
    ["Best Results", "Diagnostics", "Benchmarks", "#91 Family Evidence", "Certified Configs"]
)

with tab_best:
    st.subheader("Best configurations from SQLite")
    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No experiment rows yet. Run run_experiments.py first.")

with tab_chart:
    st.subheader("Distinct distance trends and exact gaps")
    if rows:
        df = pd.DataFrame(rows)
        if "exact_distinct_sq" in df.columns:
            df["exact_gap"] = df["exact_distinct_sq"].fillna(df["num_distinct"]) - df["num_distinct"]
        fig = px.scatter(
            df,
            x="n",
            y="num_distinct",
            color="seed_family",
            symbol="method",
            hover_data=["trial_id", "max_distinct_from_point", "energy"],
            title="Observed distinct-distance outcomes",
        )
        st.plotly_chart(fig, use_container_width=True)

        if "exact_gap" in df.columns:
            fig_gap = px.histogram(
                df,
                x="exact_gap",
                color="seed_family",
                nbins=20,
                title="Exact - approximate distinct-count gap",
            )
            st.plotly_chart(fig_gap, use_container_width=True)
    else:
        st.info("No data to chart yet.")

with tab_bench:
    st.subheader("Benchmark summaries (exact best statistics)")
    if benchmark_rows:
        bdf = pd.DataFrame(benchmark_rows)
        st.dataframe(bdf, use_container_width=True)
        fig_b = px.scatter(
            bdf,
            x="n",
            y="mean_best_exact",
            error_y=(bdf["ci95_high"] - bdf["mean_best_exact"]).clip(lower=0),
            color="run_tag",
            title="Benchmark mean best exact count with 95% CI",
        )
        st.plotly_chart(fig_b, use_container_width=True)
    else:
        st.info("No benchmark summaries yet. Use --benchmark-runs > 1.")

with tab_fam:
    st.subheader("Estimated non-similar minimizer families (#91)")
    if family_rows:
        fdf = pd.DataFrame(family_rows)
        st.dataframe(
            fdf[["run_tag", "n", "exact_distinct_sq", "family_tol", "num_candidates", "num_families", "num_signature_families", "timestamp"]],
            use_container_width=True,
        )
        fig_f = px.scatter(
            fdf,
            x="n",
            y="num_families",
            size="num_candidates",
            color="exact_distinct_sq",
            hover_data=["run_tag", "family_tol", "num_signature_families"],
            title="Shape-family counts among certified minimizers",
        )
        st.plotly_chart(fig_f, use_container_width=True)
    else:
        st.info("No family evidence rows yet. Run experiments with certification enabled.")

with tab_cert:
    st.subheader("Exact certification output")
    cert_dir = Path("certified_configs")
    if cert_dir.exists():
        records: List[Dict[str, Any]] = []
        for path in sorted(cert_dir.glob("*.json")):
            with path.open("r", encoding="utf-8") as handle:
                records.append(json.load(handle))
        if records:
            cert_df = pd.DataFrame(records)
            st.dataframe(cert_df, use_container_width=True)
        else:
            st.info("No certification JSON files found.")
    else:
        st.info("certified_configs directory does not exist yet.")
