-- Grain: one row per (match, team, player). Payload is [{team_id, team_name, lineup: [players]}].
select
    p.resource_key::int                       as match_id,
    (t ->> 'team_id')::int                    as team_id,
    t ->> 'team_name'                         as team_name,
    (pl ->> 'player_id')::int                 as player_id,
    pl ->> 'player_name'                      as player_name,
    pl ->> 'player_nickname'                  as player_nickname,
    (pl ->> 'jersey_number')::int             as jersey_number,
    pl -> 'country' ->> 'name'                as country_name,
    -- kept as JSON: spells in different positions / cards are expanded later in fact_lineup
    pl -> 'positions'                         as positions,
    pl -> 'cards'                             as cards
from {{ ref('base_statsbomb__latest_payload') }} as p
cross join lateral jsonb_array_elements(p.payload) as t
cross join lateral jsonb_array_elements(t -> 'lineup') as pl
where p.resource = 'lineups'
