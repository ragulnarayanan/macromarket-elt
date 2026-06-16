-- ===========================================================================
-- int_asset_daily_returns — one normalized daily-return stream across asset types.
--
-- Stocks and crypto live in different models with different column names. Here we
-- UNION them into a single long table: (asset_type, asset_id, asset_name, date,
-- close, daily_return). A uniform shape lets downstream models (correlations,
-- comparisons) treat every asset identically.
-- ===========================================================================

with stocks as (
    select
        'stock'        as asset_type,
        ticker         as asset_id,
        ticker         as asset_name,
        price_date     as asset_date,
        close_price    as close,
        daily_return
    from {{ ref('int_stock_prices_with_technicals') }}
),

crypto_raw as (
    select
        coin_id, symbol, price_date, price_usd,
        lag(price_usd) over (partition by coin_id order by price_date) as prev_price
    from {{ ref('int_crypto_with_dominance') }}
),

crypto as (
    select
        'crypto'    as asset_type,
        coin_id     as asset_id,
        symbol      as asset_name,
        price_date  as asset_date,
        price_usd   as close,
        {{ safe_divide('price_usd - prev_price', 'prev_price') }} as daily_return
    from crypto_raw
)

select * from stocks
union all
select * from crypto
