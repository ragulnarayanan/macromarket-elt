-- ===========================================================================
-- fct_asset_prices — per-asset, per-day prices + returns + technicals (GOLD).
--
-- WHY this exists in GOLD: the MCP server and dashboard connect as REPORTER,
-- which can read GOLD only. Per-ticker detail lives in SILVER
-- (int_stock_prices_with_technicals) — off-limits to REPORTER. This fact
-- promotes the per-asset grain into GOLD so compare_assets and asset drill-downs
-- work without weakening RBAC.
--
-- Grain: one row per (asset_type, asset_id, price_date). Stocks/indices/ETFs
-- carry technicals; crypto carries price + return (technicals are NULL).
-- ===========================================================================

with returns as (
    select * from {{ ref('int_asset_daily_returns') }}
),

technicals as (
    select ticker, price_date, ma_20, ma_50, ma_200, rsi_14
    from {{ ref('int_stock_prices_with_technicals') }}
)

select
    r.asset_type,
    r.asset_id,
    r.asset_name,
    r.asset_date as price_date,
    r.close,
    r.daily_return,
    t.ma_20,
    t.ma_50,
    t.ma_200,
    t.rsi_14
from returns r
-- attach technicals only for equities (matched by ticker)
left join technicals t
    on r.asset_type = 'stock'
   and r.asset_id = t.ticker
   and r.asset_date = t.price_date
