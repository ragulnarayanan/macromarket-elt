-- ===========================================================================
-- fct_daily_market_snapshot — the headline fact: ONE ROW PER TRADING DAY.
--
-- Stitches every source onto the date grain: equity indices, market breadth,
-- BTC, Fear & Greed, macro indicators, and the yield curve. This is what the
-- dashboard's "market overview" and the MCP get_market_snapshot tool read.
--
-- INCREMENTAL materialization (unique_key = snapshot_date, strategy = merge):
--   • first run  -> builds all dates
--   • later runs -> the is_incremental() filter processes only dates newer than
--                   what's already in the table, then MERGEs them in by
--                   snapshot_date (no duplicates, no full rebuild). This is how
--                   you keep a growing daily fact cheap.
-- ===========================================================================

{{ config(
    materialized='incremental',
    unique_key='snapshot_date',
    incremental_strategy='merge'
) }}

with technicals as (
    select * from {{ ref('int_stock_prices_with_technicals') }}
),

trading_days as (
    select distinct price_date as snapshot_date from technicals
),

-- index levels + returns, pivoted onto one row per date
indices as (
    select
        price_date,
        max(case when ticker = '^GSPC' then close_price  end) as sp500_close,
        max(case when ticker = '^GSPC' then daily_return end) as sp500_return,
        max(case when ticker = '^IXIC' then close_price  end) as nasdaq_close,
        max(case when ticker = '^DJI'  then close_price  end) as dow_close
    from technicals
    group by price_date
),

-- market breadth among the individual S&P constituents we track
breadth as (
    select
        t.price_date,
        count_if(t.daily_return > 0) as advancers,
        count_if(t.daily_return < 0) as decliners
    from technicals t
    inner join {{ ref('sp500_tickers') }} s on t.ticker = s.ticker
    group by t.price_date
),

btc as (
    select price_date, price_usd as btc_price, dominance_pct as btc_dominance
    from {{ ref('int_crypto_with_dominance') }}
    where coin_id = 'bitcoin'
),

btc_return as (
    select asset_date, daily_return as btc_return
    from {{ ref('int_asset_daily_returns') }}
    where asset_id = 'bitcoin'
),

fear_greed as (
    select reading_date, fng_value, classification as fng_classification
    from {{ ref('stg_alternative__fear_greed') }}
),

macro as (
    select observation_date, fed_funds_rate, treasury_10y, treasury_2y, vix, wti_crude_oil
    from {{ ref('int_macro_pivot') }}
),

yield_curve as (
    select observation_date, spread_10y_2y, is_inverted
    from {{ ref('int_yield_curve') }}
)

select
    d.snapshot_date,
    -- equities
    i.sp500_close,
    i.sp500_return,
    i.nasdaq_close,
    i.dow_close,
    b.advancers,
    b.decliners,
    -- crypto
    bt.btc_price,
    bt.btc_dominance,
    br.btc_return,
    -- sentiment
    fg.fng_value,
    fg.fng_classification,
    -- macro
    m.fed_funds_rate,
    m.treasury_10y,
    m.treasury_2y,
    yc.spread_10y_2y,
    yc.is_inverted,
    m.vix,
    m.wti_crude_oil
from trading_days d
left join indices     i  on d.snapshot_date = i.price_date
left join breadth     b  on d.snapshot_date = b.price_date
left join btc         bt on d.snapshot_date = bt.price_date
left join btc_return  br on d.snapshot_date = br.asset_date
left join fear_greed  fg on d.snapshot_date = fg.reading_date
left join macro       m  on d.snapshot_date = m.observation_date
left join yield_curve yc on d.snapshot_date = yc.observation_date

{% if is_incremental() %}
    -- only build dates newer than what's already loaded
    where d.snapshot_date > (select max(snapshot_date) from {{ this }})
{% endif %}
