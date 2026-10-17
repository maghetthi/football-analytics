{# Surrogate key = hash(source, natural id). Keeps warehouse keys independent of any provider's ids,
   so a second source (e.g. API-Football) can be added without colliding or rewriting facts. #}
{% macro statsbomb_key(natural_id) -%}
    {{ dbt_utils.generate_surrogate_key(["'statsbomb'", natural_id]) }}
{%- endmacro %}
