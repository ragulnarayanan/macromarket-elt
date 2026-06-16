-- ===========================================================================
-- int_macro_pivot — FRED indicators pivoted from LONG to WIDE.
--
-- Bronze/Silver store FRED as long (series_id, date, value) — flexible for
-- loading, awkward for analysis. Here we pivot to one ROW PER DATE with one
-- COLUMN PER INDICATOR, using conditional aggregation:
--     max(case when series_id = 'DFF' then value end) as fed_funds_rate
-- (max() collapses the per-series rows for a date into a single row.)
--
-- Daily series (rates, VIX, oil, FX) fill most dates; monthly/quarterly series
-- (CPI, GDP, unemployment, M2) are NULL except on release dates — expected.
-- ===========================================================================

with macro as (
    select * from {{ ref('stg_fred__macro_indicators') }}
)

select
    observation_date,
    max(case when series_id = 'DFF'        then value end) as fed_funds_rate,
    max(case when series_id = 'DGS10'      then value end) as treasury_10y,
    max(case when series_id = 'DGS2'       then value end) as treasury_2y,
    max(case when series_id = 'VIXCLS'     then value end) as vix,
    max(case when series_id = 'DCOILWTICO' then value end) as wti_crude_oil,
    max(case when series_id = 'DEXUSEU'    then value end) as usd_eur_rate,
    max(case when series_id = 'CPIAUCSL'   then value end) as cpi,
    max(case when series_id = 'UNRATE'     then value end) as unemployment_rate,
    max(case when series_id = 'M2SL'       then value end) as m2_money_supply,
    max(case when series_id = 'GDPC1'      then value end) as real_gdp
from macro
group by observation_date
