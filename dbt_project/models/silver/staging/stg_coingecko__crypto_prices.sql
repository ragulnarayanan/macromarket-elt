-- stg_coingecko__crypto_prices — typed, deduplicated crypto daily snapshot.
-- One row per (coin_id, date), latest load wins.

with source as (
    select * from {{ source('bronze', 'raw_crypto_prices') }}
),

flattened as (
    select
        raw_data:coin_id::string             as coin_id,
        raw_data:symbol::string              as symbol,
        raw_data:name::string                as coin_name,
        raw_data:date::date                  as price_date,
        raw_data:price_usd::float            as price_usd,
        raw_data:market_cap::number          as market_cap,
        raw_data:total_volume::number        as total_volume,
        raw_data:circulating_supply::float   as circulating_supply,
        raw_data:market_cap_rank::number     as market_cap_rank,
        _loaded_at                           as loaded_at
    from source
)

select *
from flattened
qualify row_number() over (
    partition by coin_id, price_date
    order by loaded_at desc
) = 1
