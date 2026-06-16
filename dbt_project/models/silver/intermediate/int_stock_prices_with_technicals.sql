-- ===========================================================================
-- int_stock_prices_with_technicals — daily prices enriched with technicals.
--
-- Adds the indicators a trader/analyst expects, computed with WINDOW FUNCTIONS
-- partitioned per ticker, ordered by date:
--   • daily_change / daily_return  (vs previous close, via LAG)
--   • moving averages 20 / 50 / 200 (macro)
--   • RSI-14 momentum               (macro, needs daily_change)
--   • Bollinger Bands 20, 2σ        (macro)
--
-- Materialized as a TABLE (project config) — heavier compute, read many times
-- downstream, so we build it once per run instead of recomputing on every read.
-- NOTE: with ~1 month of history, ma_50/ma_200 trail off to partial averages;
-- that's correct behavior, not a bug.
-- ===========================================================================

with prices as (
    select * from {{ ref('stg_yahoo__daily_prices') }}
),

with_change as (
    select
        *,
        lag(close_price) over (partition by ticker order by price_date) as prev_close,
        close_price
            - lag(close_price) over (partition by ticker order by price_date) as daily_change
    from prices
)

select
    ticker,
    price_date,
    open_price,
    high_price,
    low_price,
    close_price,
    adj_close_price,
    volume,
    daily_change,
    {{ safe_divide('daily_change', 'prev_close') }} as daily_return,

    -- moving averages (trailing N trading days)
    {{ moving_average('close_price', 'ticker', 'price_date', 20)  }} as ma_20,
    {{ moving_average('close_price', 'ticker', 'price_date', 50)  }} as ma_50,
    {{ moving_average('close_price', 'ticker', 'price_date', 200) }} as ma_200,

    -- momentum
    {{ rsi('daily_change', 'ticker', 'price_date', 14) }} as rsi_14,

    -- Bollinger Bands (20-day, 2σ)
    {{ bollinger_band('close_price', 'ticker', 'price_date', 20, 2, 'middle') }} as bb_middle,
    {{ bollinger_band('close_price', 'ticker', 'price_date', 20, 2, 'upper')  }} as bb_upper,
    {{ bollinger_band('close_price', 'ticker', 'price_date', 20, 2, 'lower')  }} as bb_lower

from with_change
