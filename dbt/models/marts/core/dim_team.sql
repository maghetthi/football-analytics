-- Latest known name per team (names can change over time).
with appearances as (
    select home_team_id as team_id, home_team_name as team_name, match_date
    from {{ ref('stg_statsbomb__matches') }}
    union all
    select away_team_id, away_team_name, match_date
    from {{ ref('stg_statsbomb__matches') }}
)

select distinct on (team_id)
    {{ statsbomb_key('team_id') }} as team_key,
    team_id                        as source_team_id,
    team_name
from appearances
order by team_id, match_date desc
