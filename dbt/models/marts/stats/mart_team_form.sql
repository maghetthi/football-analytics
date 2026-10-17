-- Grain: one row per team per match. The *_last5 columns describe the form going INTO the match
-- (the 5 previous matches, current one excluded), so they are safe as ML features: no leakage.
-- For "last N results" in the API, order this table by match_date desc and read the match columns.
with team_matches as (
    select
        match_key, competition_key, season_key, date_key, match_date,
        home_team_key as team_key, away_team_key as opponent_key, true as is_home,
        home_score as goals_for, away_score as goals_against
    from {{ ref('fact_match') }}
    union all
    select
        match_key, competition_key, season_key, date_key, match_date,
        away_team_key, home_team_key, false,
        away_score, home_score
    from {{ ref('fact_match') }}
),

shot_xg as (
    select match_key, team_key, sum(xg) as xg_for
    from {{ ref('fact_shot') }}
    where not is_shootout
    group by match_key, team_key
),

enriched as (
    select
        tm.*,
        coalesce(own.xg_for, 0)  as xg_for,
        coalesce(opp.xg_for, 0)  as xg_against,
        case
            when tm.goals_for > tm.goals_against then 'W'
            when tm.goals_for < tm.goals_against then 'L'
            else 'D'
        end                      as result
    from team_matches as tm
    left join shot_xg as own on own.match_key = tm.match_key and own.team_key = tm.team_key
    left join shot_xg as opp on opp.match_key = tm.match_key and opp.team_key = tm.opponent_key
)

select
    {{ dbt_utils.generate_surrogate_key(['match_key', 'team_key']) }} as team_match_key,
    *,
    case result when 'W' then 3 when 'D' then 1 else 0 end as points,
    count(*) over w                                        as matches_in_window,
    sum(case result when 'W' then 3 when 'D' then 1 else 0 end) over w as points_last5,
    sum(goals_for) over w                                  as goals_for_last5,
    sum(goals_against) over w                              as goals_against_last5,
    round(sum(xg_for) over w, 3)                           as xg_for_last5,
    round(sum(xg_against) over w, 3)                       as xg_against_last5
from enriched
window w as (
    partition by team_key
    order by match_date, match_key
    rows between 5 preceding and 1 preceding
)
