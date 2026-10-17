-- Each match must yield exactly one row for each side. Returned rows = failures.
select match_key, count(*) as n
from {{ ref('mart_team_form') }}
group by match_key
having count(*) <> 2
