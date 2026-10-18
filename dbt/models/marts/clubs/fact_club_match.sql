-- Grain: one row per UEFA club match, played or scheduled. result is null until it is finished.
select
    {{ dbt_utils.generate_surrogate_key(["'openligadb'", 'm.match_id']) }} as match_key,
    m.match_id                                    as source_match_id,
    c.competition_code,
    c.competition_name,
    m.season,
    {{ stage_label('m.stage_name') }}             as stage_name,
    m.kick_off_at,
    {{ club_key('m.home_team_name') }}            as home_club_key,
    {{ club_key('m.away_team_name') }}            as away_club_key,
    m.is_finished,
    case when m.is_finished then m.home_goals end as home_goals,
    case when m.is_finished then m.away_goals end as away_goals,
    case
        when not m.is_finished then null
        when m.home_goals > m.away_goals then 'home_win'
        when m.home_goals < m.away_goals then 'away_win'
        else 'draw'
    end                                           as result
from {{ ref('stg_openligadb__matches') }} as m
inner join {{ ref('openligadb_competitions') }} as c
    on m.league_shortcut = c.league_shortcut and m.season = c.season
-- Finished matches whose source score is missing or contradictory are left out, not guessed.
where not (m.is_finished and m.regulation_results_count <> 1)
