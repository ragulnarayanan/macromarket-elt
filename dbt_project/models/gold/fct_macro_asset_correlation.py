# ===========================================================================
# fct_macro_asset_correlation — dbt PYTHON model (runs on Snowflake Snowpark).
#
# WHY a Python model: some logic is clumsy in SQL. Here we compute a correlation
# matrix between asset returns and macro indicators with pandas. dbt ships the
# code to Snowflake, runs it as a Snowpark stored proc, and materializes the
# returned DataFrame as a table — no data leaves the warehouse.
#
# OUTPUT: one row per (asset, macro_indicator) with the Pearson correlation over
# the overlapping non-null days. Powers the dashboard's correlation matrix and
# the MCP get_macro_impact tool.
#
# NOTE: Snowflake Python models require your org to have accepted the Anaconda
# terms (ORGADMIN, one-time, in Snowsight: Admin > Billing & Terms). If not yet
# accepted, this model errors with a clear message — accept and re-run.
# ===========================================================================

import pandas as pd


def model(dbt, session):
    dbt.config(materialized="table", packages=["pandas"])

    # Read the daily snapshot fact as a Snowpark DataFrame -> pandas.
    # Snowflake returns column names UPPER-CASED.
    snap = dbt.ref("fct_daily_market_snapshot").to_pandas()

    asset_cols = {"SP500": "SP500_RETURN", "BTC": "BTC_RETURN"}
    macro_cols = ["VIX", "TREASURY_10Y", "TREASURY_2Y", "FED_FUNDS_RATE", "WTI_CRUDE_OIL"]

    rows = []
    for asset_name, ret_col in asset_cols.items():
        for macro in macro_cols:
            if ret_col not in snap.columns or macro not in snap.columns:
                continue
            pair = snap[[ret_col, macro]].dropna()
            # need at least 3 overlapping points for a meaningful correlation
            corr = pair[ret_col].corr(pair[macro]) if len(pair) >= 3 else None
            rows.append({
                "ASSET": asset_name,
                "MACRO_INDICATOR": macro,
                "CORRELATION": None if corr is None or pd.isna(corr) else float(corr),
                "N_OBS": int(len(pair)),
            })

    result = pd.DataFrame(rows, columns=["ASSET", "MACRO_INDICATOR", "CORRELATION", "N_OBS"])
    # Hand a Snowpark DataFrame back to dbt to materialize as a table.
    return session.create_dataframe(result)
