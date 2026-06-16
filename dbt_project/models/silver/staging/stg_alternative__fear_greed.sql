-- stg_alternative__fear_greed — typed, deduplicated Fear & Greed readings.
-- One row per date, latest load wins. value is 0-100; classification is the
-- text band (Extreme Fear ... Extreme Greed).

with source as (
    select * from {{ source('bronze', 'raw_fear_greed') }}
),

flattened as (
    select
        raw_data:date::date              as reading_date,
        raw_data:value::number           as fng_value,
        raw_data:classification::string  as classification,
        _loaded_at                       as loaded_at
    from source
)

select *
from flattened
qualify row_number() over (
    partition by reading_date
    order by loaded_at desc
) = 1
