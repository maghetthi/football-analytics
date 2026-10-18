-- Only seasons listed in the seed may be ingested: the catalogue holds many test leagues.
-- Returned rows = failures.
select distinct m.resource_key
from {{ ref('stg_openligadb__matches') }} as m
left join {{ ref('openligadb_competitions') }} as c
    on m.resource_key = c.league_shortcut || '/' || c.season::text
where c.league_shortcut is null
