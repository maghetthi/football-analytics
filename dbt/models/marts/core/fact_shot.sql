-- Grain: one row per shot. Pitch is 120x80, attacking goal at x=120, posts at y=36 and y=44.
-- is_shootout rows (period 5) are not part of open play: exclude them when modelling xG.
with shots as (
    select
        s.*,
        m.competition_id,
        m.season_id,
        m.match_date
    from {{ ref('stg_statsbomb__shots') }} as s
    inner join {{ ref('stg_statsbomb__matches') }} as m using (match_id)
)

select
    {{ statsbomb_key('event_id') }}      as shot_key,
    event_id                             as source_event_id,
    {{ statsbomb_key('match_id') }}      as match_key,
    {{ statsbomb_key('competition_id') }} as competition_key,
    {{ statsbomb_key('season_id') }}     as season_key,
    to_char(match_date, 'YYYYMMDD')::int as date_key,
    {{ statsbomb_key('team_id') }}       as team_key,
    {{ statsbomb_key('player_id') }}     as player_key,
    period,
    minute,
    second,
    location_x,
    location_y,
    end_location_x,
    end_location_y,
    end_location_z,
    sqrt(power(120 - location_x, 2) + power(40 - location_y, 2))  as distance_to_goal,
    abs(atan2(44 - location_y, 120 - location_x)
        - atan2(36 - location_y, 120 - location_x))               as shot_angle,
    xg,
    outcome,
    outcome = 'Goal'                     as is_goal,
    body_part,
    technique,
    shot_type,
    shot_type = 'Penalty'                as is_penalty,
    period = 5                           as is_shootout,
    is_first_time
from shots
