-- One row per club, identified by normalised name (OpenLigaDB ids are not stable).
-- The latest spelling wins for display.
with appearances as (
    select home_team_name as club_name, home_team_short_name as short_name, kick_off_at
    from {{ ref('stg_openligadb__matches') }}
    union all
    select away_team_name, away_team_short_name, kick_off_at
    from {{ ref('stg_openligadb__matches') }}
)

select distinct on ({{ club_key('club_name') }})
    {{ club_key('club_name') }} as club_key,
    club_name,
    short_name
from appearances
order by {{ club_key('club_name') }}, kick_off_at desc
