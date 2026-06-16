"""Regime Analysis — average asset returns per macro regime (Gold: fct_regime_analysis)."""

from __future__ import annotations

import plotly.express as px
import streamlit as st

from db import run_query

st.set_page_config(page_title="Regime Analysis", page_icon="🌡️", layout="wide")
st.title("🌡️ Macro Regime Analysis")
st.caption("Average S&P 500 return grouped by macro regime "
           "(Fed rate trend × volatility). 'How do markets behave when the Fed is hiking?'")

df = run_query(
    "SELECT rate_regime, vol_regime, num_days, avg_sp500_return, avg_btc_return "
    "FROM MACROMARKET.GOLD.fct_regime_analysis"
)
if df.empty:
    st.warning("No regime data found.")
    st.stop()

df["REGIME"] = df["RATE_REGIME"] + " / " + df["VOL_REGIME"]
df["AVG_SP500_RETURN_PCT"] = df["AVG_SP500_RETURN"] * 100

bar = px.bar(
    df.sort_values("AVG_SP500_RETURN_PCT"),
    x="AVG_SP500_RETURN_PCT", y="REGIME", orientation="h",
    color="AVG_SP500_RETURN_PCT", color_continuous_scale="RdYlGn", color_continuous_midpoint=0,
    text="NUM_DAYS",
)
bar.update_traces(texttemplate="%{text} days", textposition="outside")
bar.update_layout(height=360, margin=dict(t=20, b=10, l=10, r=10),
                  xaxis_title="Avg S&P 500 daily return %", yaxis_title=None)
st.plotly_chart(bar, width="stretch")

st.caption("With ~1 month of history these are small samples; the logic scales to full history.")
st.dataframe(
    df[["RATE_REGIME", "VOL_REGIME", "NUM_DAYS", "AVG_SP500_RETURN", "AVG_BTC_RETURN"]],
    width="stretch",
)
