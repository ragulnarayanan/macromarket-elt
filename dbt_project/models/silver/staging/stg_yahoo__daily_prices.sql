-- ===========================================================================
-- stg_yahoo__daily_prices — typed, deduplicated daily OHLCV.
--
-- THE STAGING PATTERN (every stg_ model follows this shape):
--   1. `source` CTE  : pull the raw Bronze table via the source() function.
--   2. `flattened`   : extract VARIANT fields with raw_data:field::TYPE casts.
--   3. final SELECT  : deduplicate with QUALIFY ROW_NUMBER(), keeping the most
--                      recently loaded row per natural key (ticker, date).
--
-- WHY dedup here: Bronze is append-only, so re-running a date appends rows.
-- ORDER BY loaded_at DESC + row_number()=1 keeps exactly the latest version of
-- each (ticker, date) — this is precisely why the loader stamped _loaded_at.
-- ===========================================================================

with source as (
    select * from {{ source('bronze', 'raw_stock_prices') }}
),

flattened as (
    select
        raw_data:ticker::string     as ticker,
        raw_data:date::date         as price_date,
        raw_data:open::float        as open_price,
        raw_data:high::float        as high_price,
        raw_data:low::float         as low_price,
        raw_data:close::float       as close_price,
        raw_data:adj_close::float   as adj_close_price,
        raw_data:volume::number     as volume,
        _loaded_at                  as loaded_at
    from source
)

select *
from flattened
-- keep one row per ticker/date: the most recently loaded
qualify row_number() over (
    partition by ticker, price_date
    order by loaded_at desc
) = 1
