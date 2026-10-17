-- Current version of each StatsBomb file: raw keeps every version, staging reads only the newest.
select distinct on (resource, resource_key)
    id,
    resource,
    resource_key,
    payload,
    payload_sha256,
    ingested_at
from {{ source('raw', 'source_payload') }}
where source = 'statsbomb'
order by resource, resource_key, ingested_at desc, id desc
