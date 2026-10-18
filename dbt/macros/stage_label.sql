{# OpenLigaDB stage names are German and typed by volunteers (about 60 spellings). Map them to a
   short English label; anything unrecognised is passed through unchanged. #}
{% macro stage_label(col) -%}
case
    when {{ col }} ~ '^[0-9]+\. ?(Gruppen)?[Ss]pieltag'
        then 'Matchday ' || regexp_replace({{ col }}, '^([0-9]+).*', '\1')
    when {{ col }} ~ '^Gruppe [A-H]' then 'Group ' || substring({{ col }} from '^Gruppe ([A-H])')
    when {{ col }} = 'Vorrunde' then 'Group stage'
    when {{ col }} ilike '%Play-Offs' or {{ col }} = 'Playoffs' then 'Play-offs'
    when {{ col }} ilike 'Zwischenrunde%' then 'Intermediate round'
    when {{ col }} ~ '^(Achtelfinale|Viertelfinale|Halbfinale)' then
        case substring({{ col }} from '^(Achtelfinale|Viertelfinale|Halbfinale)')
            when 'Achtelfinale' then 'Round of 16'
            when 'Viertelfinale' then 'Quarter-final'
            else 'Semi-final'
        end
        || case
            when {{ col }} ~ '(Hin|Runde 1)' then ' (1st leg)'
            when {{ col }} ~ '(R[uü]ck|Runde 2)' then ' (2nd leg)'
            else ''
        end
    when {{ col }} in ('Finale', 'Finalspiel', 'Endspiel') then 'Final'
    else {{ col }}
end
{%- endmacro %}
