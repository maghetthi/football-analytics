-- Grain: one row per on-ball/off-ball event. Common fields only; shots live in fact_shot.
select
    {{ statsbomb_key('e.event_id') }}          as event_key,
    e.event_id                                 as source_event_id,
    {{ statsbomb_key('e.match_id') }}          as match_key,
    {{ statsbomb_key('m.competition_id') }}    as competition_key,
    {{ statsbomb_key('m.season_id') }}         as season_key,
    to_char(m.match_date, 'YYYYMMDD')::int     as date_key,
    {{ statsbomb_key('e.team_id') }}           as team_key,
    case when e.player_id is not null
        then {{ statsbomb_key('e.player_id') }} end as player_key,
    e.event_index,
    e.period,
    e.minute,
    e.second,
    e.event_type,
    e.position_name,
    e.possession,
    e.play_pattern,
    e.location_x,
    e.location_y,
    e.duration,
    e.under_pressure
from {{ ref('stg_statsbomb__events') }} as e
inner join {{ ref('stg_statsbomb__matches') }} as m using (match_id)
