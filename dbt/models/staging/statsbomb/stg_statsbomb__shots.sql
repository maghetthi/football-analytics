-- Grain: one row per shot event. Source of fact_shot (xG here is StatsBomb's own model).
select
    e ->> 'id'                                         as event_id,
    p.resource_key::int                                as match_id,
    (e -> 'team' ->> 'id')::int                        as team_id,
    (e -> 'player' ->> 'id')::int                      as player_id,
    (e ->> 'period')::int                              as period,
    (e ->> 'minute')::int                              as minute,
    (e ->> 'second')::int                              as second,
    (e -> 'location' ->> 0)::numeric                   as location_x,
    (e -> 'location' ->> 1)::numeric                   as location_y,
    (s -> 'end_location' ->> 0)::numeric               as end_location_x,
    (s -> 'end_location' ->> 1)::numeric               as end_location_y,
    (s -> 'end_location' ->> 2)::numeric               as end_location_z,
    (s ->> 'statsbomb_xg')::numeric                    as xg,
    s -> 'outcome' ->> 'name'                          as outcome,
    s -> 'body_part' ->> 'name'                        as body_part,
    s -> 'technique' ->> 'name'                        as technique,
    s -> 'type' ->> 'name'                             as shot_type,
    coalesce((s ->> 'first_time')::boolean, false)     as is_first_time,
    s ->> 'key_pass_id'                                as key_pass_event_id
from {{ ref('base_statsbomb__latest_payload') }} as p
cross join lateral jsonb_array_elements(p.payload) as e
cross join lateral (select e -> 'shot' as s) as shot_detail
where p.resource = 'events'
  and e -> 'type' ->> 'name' = 'Shot'
