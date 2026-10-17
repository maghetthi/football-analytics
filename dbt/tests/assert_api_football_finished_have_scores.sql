-- A finished fixture without a score, or a team playing itself, is a broken payload. Rows = failures.
select fixture_id, status_short, home_goals, away_goals
from {{ ref('stg_api_football__fixtures') }}
where (status_short in ('FT', 'AET', 'PEN') and (home_goals is null or away_goals is null))
   or home_team_id = away_team_id
