-- Grain: one row per squad player per match (includes unused substitutes, did_play = false).
-- Match clock is continuous across periods ("50:24" = minute 50 of the match), so minutes
-- played = last exit - first entry, where an open-ended spell lasts until the final whistle.
with match_end as (
    select
        match_id,
        max(minute * 60 + second) / 60.0 as end_minute
    from {{ ref('stg_statsbomb__events') }}
    where period <= 4
    group by match_id
),

spells as (
    select
        l.match_id,
        l.team_id,
        l.player_id,
        pos ->> 'position'                                     as position_name,
        pos ->> 'start_reason'                                 as start_reason,
        (split_part(pos ->> 'from', ':', 1)::int * 60
            + split_part(pos ->> 'from', ':', 2)::int) / 60.0  as from_minute,
        (split_part(pos ->> 'to', ':', 1)::int * 60
            + split_part(pos ->> 'to', ':', 2)::int) / 60.0    as to_minute
    from {{ ref('stg_statsbomb__lineups') }} as l
    cross join lateral jsonb_array_elements(l.positions) as pos
),

played as (
    select
        s.match_id,
        s.team_id,
        s.player_id,
        bool_or(s.start_reason = 'Starting XI')                           as is_starter,
        (array_agg(s.position_name order by s.from_minute))[1]            as first_position,
        min(s.from_minute)                                                as minute_in,
        max(coalesce(s.to_minute, e.end_minute))                          as minute_out
    from spells as s
    inner join match_end as e using (match_id)
    group by s.match_id, s.team_id, s.player_id
)

select
    {{ statsbomb_key('l.match_id') }}            as match_key,
    {{ statsbomb_key('l.team_id') }}             as team_key,
    {{ statsbomb_key('l.player_id') }}           as player_key,
    {{ statsbomb_key('m.competition_id') }}      as competition_key,
    {{ statsbomb_key('m.season_id') }}           as season_key,
    to_char(m.match_date, 'YYYYMMDD')::int       as date_key,
    l.jersey_number,
    p.player_id is not null                      as did_play,
    coalesce(p.is_starter, false)                as is_starter,
    p.first_position,
    round(coalesce(p.minute_out - p.minute_in, 0)::numeric, 1) as minutes_played,
    (select count(*) from jsonb_array_elements(l.cards) as c
        where c ->> 'card_type' = 'Yellow Card')                as yellow_cards,
    (select count(*) from jsonb_array_elements(l.cards) as c
        where c ->> 'card_type' in ('Red Card', 'Second Yellow')) as red_cards
from {{ ref('stg_statsbomb__lineups') }} as l
inner join {{ ref('stg_statsbomb__matches') }} as m using (match_id)
left join played as p using (match_id, team_id, player_id)
