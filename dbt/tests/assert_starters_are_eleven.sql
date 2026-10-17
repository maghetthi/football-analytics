-- Every team starts 11 players per match. Returned rows = failures.
select match_key, team_key, count(*) as starters
from {{ ref('fact_lineup') }}
where is_starter
group by match_key, team_key
having count(*) <> 11
