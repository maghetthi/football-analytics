{{ config(severity='warn') }}
-- The source sometimes records two different regulation-time scores for one match (known case:
-- AZ Alkmaar vs Hapoel Beer Sheva, UEL 2026/27). Those matches are excluded from the marts, and this
-- warning keeps the problem visible instead of hiding it. Returned rows = warnings.
select match_id, resource_key, home_team_name, away_team_name
from {{ ref('stg_openligadb__matches') }}
where regulation_results_count > 1
