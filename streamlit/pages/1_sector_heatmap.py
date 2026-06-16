"""Sector Heatmap — daily average return by GICS sector (Gold: fct_sector_performance)."""

from __future__ import annotations

import plotly.express as px
import streamlit as st

from db import run_query

st.set_page_config(page_title="Sector Heatmap", page_icon="🗺️", layout="wide")
st.title("🗺️ Sector Heatmap")
st.caption("Daily average return by GICS sector — green = up, red = down.")

df = run_query(
    "SELECT gics_sector, price_date, avg_daily_return "
    "FROM MACROMARKET.GOLD.fct_sector_performance ORDER BY price_date"
)
if df.empty:
    st.warning("No sector performance data found.")
    st.stop()

# sector × date matrix of returns (as %), colored diverging around 0
matrix = df.pivot_table(index="GICS_SECTOR", columns="PRICE_DATE", values="AVG_DAILY_RETURN") * 100
heat = px.imshow(
    matrix,
    color_continuous_scale="RdYlGn",
    color_continuous_midpoint=0,
    aspect="auto",
    labels=dict(color="Return %"),
)
heat.update_layout(height=400, margin=dict(t=20, b=10, l=10, r=10), xaxis_title=None, yaxis_title=None)
st.plotly_chart(heat, width="stretch")

st.subheader("Cumulative return over the loaded window")
cum = (df.groupby("GICS_SECTOR")["AVG_DAILY_RETURN"].sum() * 100).sort_values().reset_index()
cum.columns = ["GICS_SECTOR", "CUMULATIVE_RETURN_PCT"]
bar = px.bar(cum, x="CUMULATIVE_RETURN_PCT", y="GICS_SECTOR", orientation="h",
             color="CUMULATIVE_RETURN_PCT", color_continuous_scale="RdYlGn", color_continuous_midpoint=0)
bar.update_layout(height=400, margin=dict(t=20, b=10, l=10, r=10), xaxis_title="Return %", yaxis_title=None)
st.plotly_chart(bar, width="stretch")
