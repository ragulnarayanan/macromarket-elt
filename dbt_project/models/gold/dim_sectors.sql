-- dim_sectors — canonical GICS sectors + description, with the Yahoo label that
-- maps to each (so facts using either naming can join). One row per sector.

select
    gics_sector,
    yahoo_sector,
    description
from {{ ref('gics_sectors') }}
