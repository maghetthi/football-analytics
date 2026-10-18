-- Grain: one row per match (played or scheduled). Payload per file is a JSON array of matches.
-- Goals come from the result named "Endergebnis" (score at the end of official time), which is what a
-- 1X2 prediction is about. Matched by NAME because the numeric resultTypeID is used inconsistently
-- by the volunteers (0, 2 or 5 depending on the season). Extra time and penalties are ignored.
with matches as (
    select p.resource_key, m
    from {{ ref('base_openligadb__latest_payload') }} as p
    cross join lateral jsonb_array_elements(p.payload) as m
    where p.resource = 'matches'
)

select
    (m ->> 'matchID')::int                                   as match_id,
    resource_key,
    split_part(resource_key, '/', 1)                         as league_shortcut,
    split_part(resource_key, '/', 2)::int                    as season,
    (m ->> 'matchDateTimeUTC')::timestamptz                  as kick_off_at,
    m -> 'group' ->> 'groupName'                             as stage_name,
    (m -> 'team1' ->> 'teamId')::int                         as home_team_id,
    m -> 'team1' ->> 'teamName'                              as home_team_name,
    m -> 'team1' ->> 'shortName'                             as home_team_short_name,
    (m -> 'team2' ->> 'teamId')::int                         as away_team_id,
    m -> 'team2' ->> 'teamName'                              as away_team_name,
    m -> 'team2' ->> 'shortName'                             as away_team_short_name,
    (m ->> 'matchIsFinished')::boolean                       as is_finished,
    res.n                                                    as regulation_results_count,
    -- A score is only trusted when the source gives exactly one regulation-time result.
    case when res.n = 1 then res.home end                    as home_goals,
    case when res.n = 1 then res.away end                    as away_goals,
    (m ->> 'lastUpdateDateTime')::timestamp                  as last_updated_at
from matches
cross join lateral (
    select
        count(*)                       as n,
        min((r ->> 'pointsTeam1')::int) as home,
        min((r ->> 'pointsTeam2')::int) as away
    from jsonb_array_elements(m -> 'matchResults') as r
    where r ->> 'resultName' = 'Endergebnis'
) as res
