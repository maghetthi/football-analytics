{# Newest raw version of each file of one source: raw keeps every version, staging reads the latest. #}
{% macro latest_payload(source_name) -%}
select distinct on (resource, resource_key)
    id,
    resource,
    resource_key,
    payload,
    payload_sha256,
    ingested_at
from {{ source('raw', 'source_payload') }}
where source = '{{ source_name }}'
order by resource, resource_key, ingested_at desc, id desc
{%- endmacro %}
