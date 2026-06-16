-- stg_yahoo__fundamentals — typed, deduplicated company fundamentals snapshot.
-- One row per (ticker, snapshot date), latest load wins.

with source as (
    select * from {{ source('bronze', 'raw_stock_fundamentals') }}
),

flattened as (
    select
        raw_data:ticker::string      as ticker,
        raw_data:date::date          as snapshot_date,
        raw_data:market_cap::number  as market_cap,
        raw_data:pe_ratio::float     as pe_ratio,
        raw_data:sector::string      as sector,
        raw_data:industry::string    as industry,
        raw_data:short_name::string  as company_name,
        _loaded_at                   as loaded_at
    from source
)

select *
from flattened
qualify row_number() over (
    partition by ticker, snapshot_date
    order by loaded_at desc
) = 1
