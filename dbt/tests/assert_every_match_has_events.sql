-- Every available match must have been ingested with events. Returned rows = failures.
select m.match_id
from {{ ref('stg_statsbomb__matches') }} as m
left join {{ ref('stg_statsbomb__events') }} as e using (match_id)
where m.match_status = 'available'
group by m.match_id
having count(e.event_id) = 0
