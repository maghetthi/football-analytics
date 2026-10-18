{# OpenLigaDB team ids are not stable (the same club can have several ids), so clubs are identified
   by normalised name. Same surrogate scheme as statsbomb_key, different source. #}
{% macro club_key(team_name) -%}
    {{ dbt_utils.generate_surrogate_key(["'openligadb'", "lower(trim(" ~ team_name ~ "))"]) }}
{%- endmacro %}
