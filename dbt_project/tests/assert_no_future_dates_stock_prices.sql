-- Singular test: stock price dates must never be in the future.
-- A SINGULAR TEST is just a SELECT — dbt FAILS the test if it returns ANY rows.
-- A future price_date would signal a timezone bug or bad source data.

select ticker, price_date
from {{ ref('stg_yahoo__daily_prices') }}
where price_date > current_date
