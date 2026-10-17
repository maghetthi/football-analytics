-- Grain: one row per fixture. Payload per file is {"response": [fixture, ...]}.
-- Goals here are final scores as the provider reports them (see `goals` vs `score`).
select
    (f -> 'fixture' ->> 'id')::int                        as fixture_id,
    (f -> 'league' ->> 'id')::int                         as league_id,
    f -> 'league' ->> 'name'                              as league_name,
    (f -> 'league' ->> 'season')::int                     as season,
    f -> 'league' ->> 'round'                             as round,
    (f -> 'fixture' ->> 'date')::timestamptz              as kick_off_at,
    f -> 'fixture' -> 'status' ->> 'short'                as status_short,
    f -> 'fixture' -> 'status' ->> 'long'                 as status_long,
    f -> 'fixture' -> 'venue' ->> 'name'                  as venue_name,
    f -> 'fixture' ->> 'referee'                          as referee_name,
    (f -> 'teams' -> 'home' ->> 'id')::int                as home_team_id,
    f -> 'teams' -> 'home' ->> 'name'                     as home_team_name,
    (f -> 'teams' -> 'away' ->> 'id')::int                as away_team_id,
    f -> 'teams' -> 'away' ->> 'name'                     as away_team_name,
    (f -> 'goals' ->> 'home')::int                        as home_goals,
    (f -> 'goals' ->> 'away')::int                        as away_goals,
    (f -> 'score' -> 'halftime' ->> 'home')::int          as home_goals_halftime,
    (f -> 'score' -> 'halftime' ->> 'away')::int          as away_goals_halftime,
    (f -> 'score' -> 'penalty' ->> 'home')::int           as home_penalty_goals,
    (f -> 'score' -> 'penalty' ->> 'away')::int           as away_penalty_goals
from {{ ref('base_api_football__latest_payload') }} as p
cross join lateral jsonb_array_elements(p.payload -> 'response') as f
where p.resource = 'fixtures'
