-- Goals in the player mart must equal goals in fact_shot (no rows lost or duplicated). Returned row = failure.
select m.goals as mart_goals, f.goals as fact_goals
from (select sum(goals) as goals from {{ ref('mart_player_season_stats') }}) as m
cross join (
    select count(*) filter (where is_goal) as goals
    from {{ ref('fact_shot') }}
    where not is_shootout
) as f
where m.goals <> f.goals
