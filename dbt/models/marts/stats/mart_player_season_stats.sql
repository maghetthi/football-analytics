-- Grain: one row per player per competition per season. Shootout kicks are excluded from shooting
-- stats. xG per 90 uses minutes from fact_lineup; assists are not modelled yet (needs pass events).
with appearances as (
    select
        player_key, competition_key, season_key,
        count(*) filter (where did_play)        as appearances,
        count(*) filter (where is_starter)      as starts,
        sum(minutes_played)                     as minutes_played,
        sum(yellow_cards)                       as yellow_cards,
        sum(red_cards)                          as red_cards
    from {{ ref('fact_lineup') }}
    group by player_key, competition_key, season_key
),

shooting as (
    select
        player_key, competition_key, season_key,
        count(*)                                        as shots,
        count(*) filter (where is_goal)                 as goals,
        count(*) filter (where is_goal and is_penalty)  as penalty_goals,
        sum(xg)                                         as xg,
        sum(xg) filter (where not is_penalty)           as np_xg
    from {{ ref('fact_shot') }}
    where not is_shootout
    group by player_key, competition_key, season_key
)

select
    {{ dbt_utils.generate_surrogate_key(['a.player_key', 'a.competition_key', 'a.season_key']) }}
                                                    as player_season_key,
    a.player_key,
    a.competition_key,
    a.season_key,
    p.player_name,
    c.competition_name,
    s.season_name,
    a.appearances,
    a.starts,
    a.minutes_played,
    a.yellow_cards,
    a.red_cards,
    coalesce(sh.shots, 0)                           as shots,
    coalesce(sh.goals, 0)                           as goals,
    coalesce(sh.penalty_goals, 0)                   as penalty_goals,
    round(coalesce(sh.xg, 0), 3)                    as xg,
    round(coalesce(sh.np_xg, 0), 3)                 as np_xg,
    round(coalesce(sh.goals, 0) - coalesce(sh.xg, 0), 3) as goals_minus_xg,
    round(coalesce(sh.np_xg, 0) / nullif(a.minutes_played, 0) * 90, 3) as np_xg_per_90
from appearances as a
inner join {{ ref('dim_player') }} as p using (player_key)
inner join {{ ref('dim_competition') }} as c using (competition_key)
inner join {{ ref('dim_season') }} as s using (season_key)
left join shooting as sh using (player_key, competition_key, season_key)
