select distinct on (season_id)
    {{ statsbomb_key('season_id') }}                         as season_key,
    season_id                                                as source_season_id,
    season_name,
    substring(season_name from '^[0-9]{4}')::int             as start_year
from {{ ref('stg_statsbomb__competitions') }}
order by season_id
