-- Grain: one row per match. Scores exclude penalty shootouts (verified against shot events).
select
    {{ statsbomb_key('m.match_id') }}          as match_key,
    m.match_id                                 as source_match_id,
    {{ statsbomb_key('m.competition_id') }}    as competition_key,
    {{ statsbomb_key('m.season_id') }}         as season_key,
    to_char(m.match_date, 'YYYYMMDD')::int     as date_key,
    {{ statsbomb_key('m.home_team_id') }}      as home_team_key,
    {{ statsbomb_key('m.away_team_id') }}      as away_team_key,
    m.match_date,
    m.kick_off,
    m.stage_name,
    m.match_week,
    m.stadium_name,
    m.referee_name,
    m.home_score,
    m.away_score,
    m.home_score - m.away_score                as goal_difference,
    case
        when m.home_score > m.away_score then 'home_win'
        when m.home_score < m.away_score then 'away_win'
        else 'draw'
    end                                        as result
from {{ ref('stg_statsbomb__matches') }} as m
where m.match_status = 'available'
