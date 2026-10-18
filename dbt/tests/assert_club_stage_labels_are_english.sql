-- Every stage must have been translated; an untranslated German name means a new spelling
-- appeared in the source and macros/stage_label.sql needs a rule. Returned rows = failures.
select distinct stage_name
from {{ ref('fact_club_match') }}
where stage_name ~ '(spieltag|Spieltag|finale|Finale|Runde|Gruppe|Rück|Hin)'
