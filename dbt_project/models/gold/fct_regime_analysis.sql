-- ===========================================================================
-- fct_regime_analysis — average asset returns grouped by MACRO REGIME.
--
-- Two regime axes, labeled per day from the snapshot fact:
--   • rate_regime : Hiking / Cutting / Holding — sign of the change in the Fed
--                   funds rate vs ~5 trading days ago.
--   • vol_regime  : High Vol / Low Vol — VIX above/below 20.
-- Then we aggregate: for each regime combo, the average S&P and BTC return and
-- the number of days observed. "During hiking + high-vol, how did stocks do?"
--
-- (With ~1 month of data this yields a few rows; the logic scales to full history.)
-- ===========================================================================

with daily as (
    select
        snapshot_date,
        sp500_return,
        btc_return,
        vix,
        fed_funds_rate,
        lag(fed_funds_rate, 5) over (order by snapshot_date) as fed_funds_prev
    from {{ ref('fct_daily_market_snapshot') }}
),

labeled as (
    select
        snapshot_date,
        sp500_return,
        btc_return,
        case
            when fed_funds_rate > fed_funds_prev then 'Hiking'
            when fed_funds_rate < fed_funds_prev then 'Cutting'
            else 'Holding'
        end as rate_regime,
        case when vix >= 20 then 'High Vol' else 'Low Vol' end as vol_regime
    from daily
)

select
    rate_regime,
    vol_regime,
    count(*)            as num_days,
    avg(sp500_return)   as avg_sp500_return,
    avg(btc_return)     as avg_btc_return
from labeled
group by rate_regime, vol_regime
order by rate_regime, vol_regime
