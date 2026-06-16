-- dim_macro_indicators — descriptive metadata for each FRED series.
-- Sourced from the fred_series_metadata seed. Join facts on series_id to get a
-- human-readable name, frequency, unit, and category.

select
    series_id,
    series_name,
    frequency,
    unit,
    category
from {{ ref('fred_series_metadata') }}
