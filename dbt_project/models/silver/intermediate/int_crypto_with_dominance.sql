-- ===========================================================================
-- int_crypto_with_dominance — crypto prices + market-cap dominance %.
--
-- "Dominance" = a coin's market cap as a share of the total crypto market cap
-- that day. BTC dominance especially is a risk-on/risk-off sentiment gauge.
-- We compute the per-date total with a window SUM, then divide.
-- ===========================================================================

with crypto as (
    select * from {{ ref('stg_coingecko__crypto_prices') }}
),

with_total as (
    select
        *,
        sum(market_cap) over (partition by price_date) as total_market_cap_day
    from crypto
)

select
    coin_id,
    symbol,
    coin_name,
    price_date,
    price_usd,
    market_cap,
    total_volume,
    circulating_supply,
    market_cap_rank,
    100 * {{ safe_divide('market_cap', 'total_market_cap_day') }} as dominance_pct
from with_total
