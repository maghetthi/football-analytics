.DEFAULT_GOAL := help
PY := .venv/bin/python
COMPOSE := docker compose

.PHONY: predict-clubs ingest-openligadb ingest-openligadb-current ingest-statsbomb-clubs neon-check neon-migrate neon-publish help ingest-statsbomb-all api dashboard train hooks venv up down logs reset-db psql migrate ingest-statsbomb dbt-deps dbt-build test lint fmt

help: ## Show targets
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-18s %s\n", $$1, $$2}'

venv: ## Create .venv (Python 3.12) and install deps
	uv venv --python 3.12 .venv
	uv pip install --python $(PY) -e ".[dev,dbt,api,ml,dashboard,flows]"

hooks: ## Install git pre-commit and commit-msg hooks
	.venv/bin/pre-commit install --hook-type pre-commit --hook-type commit-msg

up: ## Start Postgres + Redis and wait until healthy
	$(COMPOSE) up -d --wait

down: ## Stop containers (keeps data)
	$(COMPOSE) down

logs: ## Tail container logs
	$(COMPOSE) logs -f

reset-db: ## DESTROY the Postgres volume and start clean
	$(COMPOSE) down -v
	$(COMPOSE) up -d --wait

psql: ## Open psql inside the Postgres container
	$(COMPOSE) exec postgres sh -c 'psql -U $$POSTGRES_USER -d $$POSTGRES_DB'

migrate: ## Apply Alembic migrations
	$(PY) -m alembic -c infra/alembic.ini upgrade head

ingest-statsbomb: ## Ingest StatsBomb into raw (COMP=43 SEASON=106)
	$(PY) -m football_pipeline.ingest_statsbomb --competition $${COMP:-43} --season $${SEASON:-106}

ingest-statsbomb-all: ## Ingest all modern men's international tournaments (~300 matches, ~10 min)
	for cs in 43:3 43:106 55:43 55:282 223:282 1267:107; do \
		COMP=$${cs%%:*} SEASON=$${cs##*:} $(MAKE) --no-print-directory ingest-statsbomb || exit 1; \
	done

ingest-statsbomb-clubs: ## Ingest StatsBomb Premier League + La Liga (~1,300 matches, ~20 min, ~800 MB raw)
	for cs in 2:44 2:27 11:278 11:37 11:38 11:39 11:40 11:41 11:21 11:22 11:23 11:24 11:25 11:26 11:27 11:2 11:1 11:4 11:42 11:90; do \
		COMP=$${cs%%:*} SEASON=$${cs##*:} $(MAKE) --no-print-directory ingest-statsbomb || exit 1; \
	done

ingest-openligadb: ## Ingest UEFA club competitions (UCL/UEL/UECL) from OpenLigaDB, all seasons
	$(PY) -m football_pipeline.flows openligadb

ingest-openligadb-current: ## Re-read only the live season (what the daily job runs)
	$(PY) -m football_pipeline.flows openligadb --current-only

# Loads .env when present (local); in CI the variables come from the workflow env.
DBT := set -a; [ -f .env ] && . ./.env; set +a; .venv/bin/dbt

dbt-deps: ## Install dbt packages
	$(DBT) deps --project-dir dbt --profiles-dir dbt

dbt-build: ## Run dbt models + tests
	$(DBT) build --project-dir dbt --profiles-dir dbt

api: ## Run the API with reload (needs make up, migrate, dbt-build)
	.venv/bin/uvicorn football_api.main:app --reload

train: ## Train and evaluate the match model (needs dbt-build); logs to MLflow
	$(PY) -m football_ml.train

predict-clubs: ## Evaluate club models and write predictions for scheduled UEFA matches (DRY=1 to skip writing)
	$(PY) -m football_ml.clubs $${DRY:+--dry-run}

dashboard: ## Run the Streamlit dashboard (needs make api)
	set -a; [ -f .env ] && . ./.env; set +a; DASHBOARD_API_KEY=$${DASHBOARD_API_KEY:-$${API_KEYS%%,*}} .venv/bin/streamlit run services/dashboard/app.py

# Remote database ("neon-*"): credentials live in .env.neon (gitignored), never on the command line.
NEON := set -a; . ./.env.neon; set +a

neon-check: ## Check the remote DB from .env.neon (no secrets printed)
	$(NEON); $(PY) -m football_pipeline.check_db

neon-migrate: ## Apply migrations to the remote DB from .env.neon
	$(NEON); $(PY) -m alembic -c infra/alembic.ini upgrade head

neon-publish: ## Copy the serving marts from the local warehouse to the remote DB
	$(NEON); infra/scripts/publish_marts.sh

test: ## Run tests
	$(PY) -m pytest

lint: ## Ruff lint + format check
	$(PY) -m ruff check .
	$(PY) -m ruff format --check .

fmt: ## Ruff autofix + format
	$(PY) -m ruff check --fix .
	$(PY) -m ruff format .
