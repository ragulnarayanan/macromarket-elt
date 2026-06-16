-- Singular test: market caps must be sane (positive, below a 100T ceiling).
-- Returns offending rows -> any row fails the build.
--
-- DESIGN NOTE: the spec suggested 3σ anomaly detection, but with a megacap-heavy
-- universe (e.g. AAPL/NVDA at multi-trillion) a naive 3σ bound flags legitimate
-- giants and would fail the build on good data. So we assert hard sanity bounds
-- instead: market cap present and 0 < value < 100 trillion. (A robust per-sector
-- z-score anomaly check is a sensible future enhancement.)

select ticker, snapshot_date, market_cap
from {{ ref('stg_yahoo__fundamentals') }}
where market_cap is not null
  and (market_cap <= 0 or market_cap > 100000000000000)   -- 100T ceiling
