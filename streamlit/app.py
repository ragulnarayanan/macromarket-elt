"""
app.py — MacroMarket dashboard home: Market Overview.

Reads the Gold daily snapshot fact (as REPORTER) and shows the latest market
picture: headline KPIs, a Fear & Greed gauge, and the S&P 500 trend. Additional
views live under pages/ (sidebar).

Run:  streamlit run streamlit/app.py
"""

from __future__ import annotations

import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

from db import run_query

st.set_page_config(page_title="MacroMarket", page_icon="📈", layout="wide")

st.title("📈 MacroMarket — Market Overview")
st.caption("Daily market snapshot from the Snowflake Gold layer (read-only, REPORTER role).")

snapshot = run_query(
    "SELECT * FROM MACROMARKET.GOLD.fct_daily_market_snapshot ORDER BY snapshot_date"
)

if snapshot.empty:
    st.warning("No snapshot data found in GOLD.fct_daily_market_snapshot.")
    st.stop()

latest = snapshot.iloc[-1]
prev = snapshot.iloc[-2] if len(snapshot) > 1 else latest
st.subheader(f"As of {latest['SNAPSHOT_DATE']}")


def _fmt(v, prefix="", suffix="", nd=2):
    return f"{prefix}{v:,.{nd}f}{suffix}" if v is not None and v == v else "—"


# --- Headline KPIs ---------------------------------------------------------
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("S&P 500", _fmt(latest["SP500_CLOSE"]),
          _fmt((latest["SP500_RETURN"] or 0) * 100, suffix="%") if latest["SP500_RETURN"] is not None else None)
c2.metric("Bitcoin", _fmt(latest["BTC_PRICE"], prefix="$", nd=0))
c3.metric("Fear & Greed", _fmt(latest["FNG_VALUE"], nd=0), latest["FNG_CLASSIFICATION"], delta_color="off")
c4.metric("10Y Treasury", _fmt(latest["TREASURY_10Y"], suffix="%"))
c5.metric("VIX", _fmt(latest["VIX"]))

st.divider()

# --- Fear & Greed gauge + S&P trend ---------------------------------------
left, right = st.columns([1, 2])

with left:
    st.markdown("**Fear & Greed Index**")
    fng = latest["FNG_VALUE"]
    gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=float(fng) if fng is not None else 0,
        title={"text": latest["FNG_CLASSIFICATION"] or ""},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": "black"},
            "steps": [
                {"range": [0, 25], "color": "#d62728"},    # extreme fear
                {"range": [25, 45], "color": "#ff7f0e"},    # fear
                {"range": [45, 55], "color": "#f7e463"},    # neutral
                {"range": [55, 75], "color": "#9bd770"},    # greed
                {"range": [75, 100], "color": "#2ca02c"},   # extreme greed
            ],
        },
    ))
    gauge.update_layout(height=280, margin=dict(t=40, b=10, l=20, r=20))
    st.plotly_chart(gauge, width="stretch")

with right:
    st.markdown("**S&P 500 close**")
    fig = px.line(snapshot, x="SNAPSHOT_DATE", y="SP500_CLOSE", markers=True)
    fig.update_layout(height=280, margin=dict(t=20, b=10, l=10, r=10),
                      xaxis_title=None, yaxis_title=None)
    st.plotly_chart(fig, width="stretch")

# --- Market breadth + yield curve -----------------------------------------
st.divider()
b1, b2, b3 = st.columns(3)
b1.metric("Advancers", _fmt(latest["ADVANCERS"], nd=0))
b2.metric("Decliners", _fmt(latest["DECLINERS"], nd=0))
spread = latest["SPREAD_10Y_2Y"]
b3.metric("10Y–2Y spread", _fmt(spread, suffix=" pp"),
          "Inverted ⚠️" if (spread is not None and spread < 0) else "Normal", delta_color="off")

with st.expander("Raw snapshot data"):
    st.dataframe(snapshot, width="stretch")
