select
    (m ->> 'match_id')::int                          as match_id,
    (m -> 'competition' ->> 'competition_id')::int   as competition_id,
    (m -> 'season' ->> 'season_id')::int             as season_id,
    (m ->> 'match_date')::date                       as match_date,
    (m ->> 'kick_off')::time                         as kick_off,
    m ->> 'match_status'                             as match_status,
    (m ->> 'match_week')::int                        as match_week,
    (m -> 'competition_stage' ->> 'id')::int         as stage_id,
    m -> 'competition_stage' ->> 'name'              as stage_name,
    (m -> 'home_team' ->> 'home_team_id')::int       as home_team_id,
    m -> 'home_team' ->> 'home_team_name'            as home_team_name,
    (m -> 'away_team' ->> 'away_team_id')::int       as away_team_id,
    m -> 'away_team' ->> 'away_team_name'            as away_team_name,
    (m ->> 'home_score')::int                        as home_score,
    (m ->> 'away_score')::int                        as away_score,
    (m -> 'stadium' ->> 'id')::int                   as stadium_id,
    m -> 'stadium' ->> 'name'                        as stadium_name,
    (m -> 'referee' ->> 'id')::int                   as referee_id,
    m -> 'referee' ->> 'name'                        as referee_name,
    (m ->> 'last_updated')::timestamp                as last_updated_at
from {{ ref('base_statsbomb__latest_payload') }} as p
cross join lateral jsonb_array_elements(p.payload) as m
where p.resource = 'matches'
