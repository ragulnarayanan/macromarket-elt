"""Macro Correlations — asset returns vs macro indicators (Gold: fct_macro_asset_correlation)."""

from __future__ import annotations

import plotly.express as px
import streamlit as st

from db import run_query

st.set_page_config(page_title="Macro Correlations", page_icon="🔗", layout="wide")
st.title("🔗 Macro / Asset Correlations")
st.caption("Pearson correlation between each asset's daily returns and macro indicators. "
           "Blue = positive, red = negative. Blank = insufficient overlapping data.")

df = run_query(
    "SELECT asset, macro_indicator, correlation "
    "FROM MACROMARKET.GOLD.fct_macro_asset_correlation"
)
if df.empty:
    st.warning("No correlation data found.")
    st.stop()

matrix = df.pivot(index="ASSET", columns="MACRO_INDICATOR", values="CORRELATION")
heat = px.imshow(
    matrix,
    color_continuous_scale="RdBu",
    zmin=-1, zmax=1,
    text_auto=".2f",
    aspect="auto",
    labels=dict(color="correlation"),
)
heat.update_layout(height=320, margin=dict(t=20, b=10, l=10, r=10), xaxis_title=None, yaxis_title=None)
st.plotly_chart(heat, width="stretch")

st.info(
    "Note: BTC correlations are blank — CoinGecko's snapshot endpoint has only been "
    "captured once, so crypto has no return series yet. This fills in as the daily "
    "pipeline accumulates history.",
    icon="ℹ️",
)

with st.expander("Raw correlations"):
    st.dataframe(df, width="stretch")
