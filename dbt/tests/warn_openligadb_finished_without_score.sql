{{ config(severity='warn') }}
-- A match flagged finished that has no regulation-time score yet: volunteers may be late (live
-- season) or never entered it (8 round-of-16 matches of 2016/17). They are excluded from the
-- marts, not guessed. Returned rows = warnings.
select match_id, resource_key, home_team_name, away_team_name
from {{ ref('stg_openligadb__matches') }}
where is_finished and regulation_results_count = 0
