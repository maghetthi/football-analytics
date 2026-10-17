-- Latest known name per player: the same player_id appears with spelling variants across matches.
select distinct on (l.player_id)
    {{ statsbomb_key('l.player_id') }} as player_key,
    l.player_id                        as source_player_id,
    l.player_name,
    l.player_nickname,
    l.country_name
from {{ ref('stg_statsbomb__lineups') }} as l
inner join {{ ref('stg_statsbomb__matches') }} as m using (match_id)
order by l.player_id, m.match_date desc, l.match_id desc
