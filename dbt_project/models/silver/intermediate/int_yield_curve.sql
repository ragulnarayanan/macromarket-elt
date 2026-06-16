-- ===========================================================================
-- int_yield_curve — 10Y minus 2Y Treasury spread + inversion flag.
--
-- The 10Y-2Y spread is a watched macro signal: when it goes NEGATIVE (the curve
-- "inverts"), short rates exceed long rates — historically a recession warning.
-- One row per date where both yields are present.
-- ===========================================================================

with macro as (
    select observation_date, treasury_10y, treasury_2y
    from {{ ref('int_macro_pivot') }}
    where treasury_10y is not null and treasury_2y is not null
)

select
    observation_date,
    treasury_10y,
    treasury_2y,
    treasury_10y - treasury_2y          as spread_10y_2y,
    (treasury_10y - treasury_2y) < 0    as is_inverted
from macro
