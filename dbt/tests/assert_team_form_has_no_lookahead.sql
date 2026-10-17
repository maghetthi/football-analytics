-- A team's first match has no prior form; later ones count at most the matches already played.
-- Returned rows = failures.
select team_match_key
from {{ ref('mart_team_form') }}
where matches_in_window > 5
   or (matches_in_window = 0 and points_last5 is not null)
