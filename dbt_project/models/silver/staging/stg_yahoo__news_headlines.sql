-- stg_yahoo__news_headlines — typed, deduplicated headlines (FinBERT input).
-- These feed the Databricks sentiment job in Phase 5.
--
-- Dedup key: (ticker, url) — the same article can appear across runs; URL is the
-- natural unique id, with headline as a fallback when URL is missing.
-- published_date arrives as a string (ISO or epoch); we keep the raw string and
-- also derive a best-effort timestamp with TRY_TO_TIMESTAMP (NULL if unparseable).

with source as (
    select * from {{ source('bronze', 'raw_news_headlines') }}
),

flattened as (
    select
        raw_data:ticker::string          as ticker,
        raw_data:headline::string        as headline,
        raw_data:publisher::string       as publisher,
        raw_data:published_date::string  as published_date_raw,
        try_to_timestamp(raw_data:published_date::string) as published_at,
        raw_data:url::string             as url,
        raw_data:extracted_date::date    as extracted_date,
        _loaded_at                       as loaded_at
    from source
)

select *
from flattened
qualify row_number() over (
    partition by ticker, coalesce(url, headline)
    order by loaded_at desc
) = 1
