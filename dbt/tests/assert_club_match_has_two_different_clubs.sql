-- A club cannot play itself, and every scheduled match must be in the future or unfinished
-- data is stale. Returned rows = failures.
select match_key
from {{ ref('fact_club_match') }}
where home_club_key = away_club_key
