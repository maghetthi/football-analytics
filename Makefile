.DEFAULT_GOAL := help
PY := .venv/bin/python
COMPOSE := docker compose

.PHONY: help venv up down logs reset-db psql migrate ingest-statsbomb dbt-deps dbt-build test lint fmt

help: ## Show targets
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-18s %s\n", $$1, $$2}'

venv: ## Create .venv (Python 3.12) and install deps
	uv venv --python 3.12 .venv
	uv pip install --python $(PY) -e ".[dev,dbt]"

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

DBT := set -a; . ./.env; set +a; .venv/bin/dbt

dbt-deps: ## Install dbt packages
	$(DBT) deps --project-dir dbt --profiles-dir dbt

dbt-build: ## Run dbt models + tests
	$(DBT) build --project-dir dbt --profiles-dir dbt

test: ## Run tests
	$(PY) -m pytest

lint: ## Ruff lint + format check
	$(PY) -m ruff check .
	$(PY) -m ruff format --check .

fmt: ## Ruff autofix + format
	$(PY) -m ruff check --fix .
	$(PY) -m ruff format .
