-- Grain: one row per event. Common fields only; type-specific detail (shots, passes...) gets its own model.
select
    e ->> 'id'                                  as event_id,
    p.resource_key::int                         as match_id,
    (e ->> 'index')::int                        as event_index,
    (e ->> 'period')::int                       as period,
    (e ->> 'minute')::int                       as minute,
    (e ->> 'second')::int                       as second,
    e ->> 'timestamp'                           as match_timestamp,
    (e -> 'type' ->> 'id')::int                 as event_type_id,
    e -> 'type' ->> 'name'                      as event_type,
    (e -> 'team' ->> 'id')::int                 as team_id,
    e -> 'team' ->> 'name'                      as team_name,
    (e -> 'player' ->> 'id')::int               as player_id,
    e -> 'player' ->> 'name'                    as player_name,
    e -> 'position' ->> 'name'                  as position_name,
    (e ->> 'possession')::int                   as possession,
    (e -> 'possession_team' ->> 'id')::int      as possession_team_id,
    e -> 'play_pattern' ->> 'name'              as play_pattern,
    (e -> 'location' ->> 0)::numeric            as location_x,
    (e -> 'location' ->> 1)::numeric            as location_y,
    (e ->> 'duration')::numeric                 as duration,
    coalesce((e ->> 'under_pressure')::boolean, false) as under_pressure
from {{ ref('base_statsbomb__latest_payload') }} as p
cross join lateral jsonb_array_elements(p.payload) as e
where p.resource = 'events'
