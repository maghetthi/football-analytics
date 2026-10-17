-- fact_shot must not silently drop shots in the join chain. Returned row = failure.
select s.n as staging_shots, f.n as fact_shots
from (select count(*) as n from {{ ref('stg_statsbomb__shots') }}) as s
cross join (select count(*) as n from {{ ref('fact_shot') }}) as f
where s.n <> f.n
