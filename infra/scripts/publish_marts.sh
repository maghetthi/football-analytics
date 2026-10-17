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

: "${TARGET_DATABASE_URL:?set TARGET_DATABASE_URL (it is read from the environment so it never lands in shell history or the repo)}"

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
