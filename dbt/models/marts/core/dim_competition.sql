select distinct on (competition_id)
    {{ statsbomb_key('competition_id') }} as competition_key,
    competition_id                        as source_competition_id,
    competition_name,
    country_name,
    competition_gender,
    is_youth,
    is_international
from {{ ref('stg_statsbomb__competitions') }}
order by competition_id, match_updated_at desc nulls last
