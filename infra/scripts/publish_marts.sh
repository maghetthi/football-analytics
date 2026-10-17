#!/usr/bin/env bash
# Copy the serving tables (marts, without fact_event) from the local warehouse to a remote Postgres.
#
# Why a copy and not "run the pipeline remotely": the full local warehouse is ~800 MB (raw + staging
# + fact_event) while the tables the API and model actually read are ~15 MB. Free managed Postgres
# plans are small, so production holds only the serving layer.
#
# Usage (remote must already be migrated: POSTGRES_* pointing at it, then `make migrate`):
# Needs only Docker (psql runs inside the local Postgres container, so no client install).
#   TARGET_DATABASE_URL='postgresql://user:pass@host/db?sslmode=require' infra/scripts/publish_marts.sh
set -euo pipefail

# Remote target: either a ready TARGET_DATABASE_URL, or built (and URL-escaped) from POSTGRES_*.
# This must happen BEFORE sourcing .env, which holds the LOCAL warehouse settings.
if [ -z "${TARGET_DATABASE_URL:-}" ]; then
  : "${POSTGRES_HOST:?set POSTGRES_* (make neon-publish loads them from .env.neon)}"
  TARGET_DATABASE_URL="$(python3 - <<'PY'
import os
from urllib.parse import quote
e = os.environ
print(
    f"postgresql://{quote(e['POSTGRES_USER'], safe='')}:{quote(e['POSTGRES_PASSWORD'], safe='')}"
    f"@{e['POSTGRES_HOST']}:{e.get('POSTGRES_PORT', '5432')}/{e['POSTGRES_DB']}"
    f"?sslmode={e.get('POSTGRES_SSLMODE') or 'require'}"
)
PY
)"
  export TARGET_DATABASE_URL
fi

set -a; [ -f .env ] && . ./.env; set +a

TABLES=(dim_competition dim_season dim_team dim_player dim_date fact_match fact_shot fact_lineup
        mart_team_form mart_player_season_stats)
ARGS=()
for t in "${TABLES[@]}"; do ARGS+=(-t "marts.$t"); done

docker compose exec -T postgres pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  --no-owner --no-privileges --clean --if-exists "${ARGS[@]}" \
  | docker compose exec -T -e TARGET_DATABASE_URL postgres \
      sh -c 'psql "$TARGET_DATABASE_URL" -v ON_ERROR_STOP=1 --quiet'

echo "Published ${#TABLES[@]} tables to the target database."
