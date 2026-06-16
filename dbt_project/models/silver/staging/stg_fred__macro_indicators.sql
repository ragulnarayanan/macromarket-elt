-- stg_fred__macro_indicators — typed, deduplicated FRED observations.
-- One row per (series_id, date), latest load wins. `value` may be NULL where
-- FRED had no reading (the extractor already converted "." to null).

with source as (
    select * from {{ source('bronze', 'raw_fred_series') }}
),

flattened as (
    select
        raw_data:series_id::string      as series_id,
        raw_data:series_name::string    as series_name,
        raw_data:date::date             as observation_date,
        raw_data:value::float           as value,
        _loaded_at                      as loaded_at
    from source
)

select *
from flattened
qualify row_number() over (
    partition by series_id, observation_date
    order by loaded_at desc
) = 1
