-- Every available staged match must appear in fact_match. Returned row = failure.
select s.n as staging_matches, f.n as fact_matches
from (
    select count(*) as n from {{ ref('stg_statsbomb__matches') }} where match_status = 'available'
) as s
cross join (select count(*) as n from {{ ref('fact_match') }}) as f
where s.n <> f.n
