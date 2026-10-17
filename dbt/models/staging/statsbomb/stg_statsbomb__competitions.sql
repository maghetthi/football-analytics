select
    (c ->> 'competition_id')::int         as competition_id,
    (c ->> 'season_id')::int              as season_id,
    c ->> 'competition_name'              as competition_name,
    c ->> 'season_name'                   as season_name,
    c ->> 'country_name'                  as country_name,
    c ->> 'competition_gender'            as competition_gender,
    (c ->> 'competition_youth')::boolean  as is_youth,
    (c ->> 'competition_international')::boolean as is_international,
    (c ->> 'match_available')::timestamp  as match_available_at,
    (c ->> 'match_updated')::timestamp    as match_updated_at
from {{ ref('base_statsbomb__latest_payload') }} as p
cross join lateral jsonb_array_elements(p.payload) as c
where p.resource = 'competitions'
