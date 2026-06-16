-- ===========================================================================
-- dim_tickers — one row per ticker: identity + classification + latest fundamentals.
--
-- A DIMENSION table = the descriptive "who/what" you join facts against.
-- Combines three inputs:
--   • sp500_tickers seed     (ticker, company name, Yahoo sector)
--   • latest fundamentals    (market cap, P/E, industry — newest snapshot/ticker)
--   • gics_sectors seed       (maps Yahoo sector -> canonical GICS sector)
-- ===========================================================================

with tickers as (
    select * from {{ ref('sp500_tickers') }}
),

latest_fundamentals as (
    select ticker, market_cap, pe_ratio, industry
    from {{ ref('stg_yahoo__fundamentals') }}
    -- keep only the most recent snapshot per ticker
    qualify row_number() over (partition by ticker order by snapshot_date desc) = 1
),

sector_map as (
    select yahoo_sector, gics_sector from {{ ref('gics_sectors') }}
)

select
    t.ticker,
    t.company_name,
    t.sector            as yahoo_sector,
    sm.gics_sector,
    f.industry,
    f.market_cap,
    f.pe_ratio
from tickers t
left join latest_fundamentals f on t.ticker = f.ticker
left join sector_map sm          on t.sector = sm.yahoo_sector
