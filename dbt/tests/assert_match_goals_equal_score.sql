-- Goals from shot events (incl. penalties in play, excl. shootouts, + own goals) must equal the final score.
-- Returned rows = failures. Own goals are events of type 'Own Goal For' credited to the scoring side.
with shot_goals as (
    select match_id, team_id, count(*) as goals
    from {{ ref('stg_statsbomb__shots') }}
    where outcome = 'Goal' and period <= 4
    group by 1, 2
),
own_goals as (
    select match_id, team_id, count(*) as goals
    from {{ ref('stg_statsbomb__events') }}
    where event_type = 'Own Goal For'
    group by 1, 2
),
event_goals as (
    select match_id, team_id, sum(goals) as goals
    from (select * from shot_goals union all select * from own_goals) as g
    group by 1, 2
)
select
    m.match_id,
    m.home_score, coalesce(h.goals, 0) as home_goals,
    m.away_score, coalesce(a.goals, 0) as away_goals
from {{ ref('stg_statsbomb__matches') }} as m
left join event_goals as h on h.match_id = m.match_id and h.team_id = m.home_team_id
left join event_goals as a on a.match_id = m.match_id and a.team_id = m.away_team_id
where m.home_score <> coalesce(h.goals, 0)
   or m.away_score <> coalesce(a.goals, 0)
