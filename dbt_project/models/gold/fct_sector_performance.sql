-- ===========================================================================
-- fct_sector_performance — daily return aggregated to the sector level.
--
-- Joins each stock's daily return to its sector (dim_tickers), then averages
-- across constituents per (sector, date). Powers the dashboard sector heatmap.
-- ===========================================================================

with prices as (
    select t.ticker, t.price_date, t.daily_return, t.close_price
    from {{ ref('int_stock_prices_with_technicals') }} t
    inner join {{ ref('sp500_tickers') }} s on t.ticker = s.ticker   -- individual stocks only
),

dim as (
    select ticker, gics_sector from {{ ref('dim_tickers') }}
)

select
    d.gics_sector,
    p.price_date,
    count(distinct p.ticker)      as num_constituents,
    avg(p.daily_return)           as avg_daily_return,
    sum(p.close_price)            as total_close_price
from prices p
inner join dim d on p.ticker = d.ticker
where d.gics_sector is not null
group by d.gics_sector, p.price_date
