# Deployment guide

Production runs only the **serving layer**. The full local warehouse is ~835 MB (raw 188 MB,
staging 239 MB, marts 399 MB of which `fact_event` is 389 MB), but the API and the model read
~15 MB of marts. Free managed Postgres plans are small, so production receives a copy of those
tables instead of re-running the pipeline.

```
laptop:  StatsBomb -> raw -> dbt -> marts ──publish_marts.sh──► managed Postgres ◄── API ◄── dashboard
                                      └─ make train ─► models/ (committed) ──baked into──► API image
```

## Before choosing providers: verify current free plans

Free tiers change often. I could not load the providers' own pricing pages while writing this, so
check these yourself before you rely on them:

| Piece | What to confirm | Why it matters |
|---|---|---|
| Managed Postgres (Neon, Supabase) | storage cap, pgvector available, `CREATE ROLE` allowed, idle suspension | marts subset is ~15 MB; the full warehouse would not fit a 0.5 GB cap |
| Redis (Upstash) | commands/month, TLS URL (`rediss://`) | cache fails open, so Redis is optional |
| App host (Render, Fly.io, Railway) | free web service exists for new accounts, cold-start behaviour, RAM (API ~250 MB, dashboard ~300 MB) | the dashboard and API are separate services |
| API-Football | **verified on a live key:** Free = 100 requests/day, 10/minute, seasons 2022-2024 only | no current-season data on the free plan; the adapter enforces the daily budget |

## Steps

1. **Create the database** and copy its connection parameters.
2. **Migrate it** (creates schemas, the `vector` extension and the read-only `api_reader` role):
   ```bash
   POSTGRES_HOST=<host> POSTGRES_USER=<user> POSTGRES_PASSWORD=<pw> POSTGRES_DB=<db> \
   POSTGRES_SSLMODE=require API_DB_PASSWORD=<new-strong-password> make migrate
   ```
3. **Publish the marts** from your local warehouse:
   ```bash
   TARGET_DATABASE_URL='postgresql://<user>:<pw>@<host>/<db>?sslmode=require' \
     infra/scripts/publish_marts.sh
   ```
4. **Deploy the API** from `services/api/Dockerfile` (build context = repo root). Environment:
   `POSTGRES_HOST`, `POSTGRES_DB`, `POSTGRES_SSLMODE=require`, `API_DB_USER=api_reader`,
   `API_DB_PASSWORD`, `API_KEYS` (comma-separated), `REDIS_URL`, optional `CACHE_TTL_SECONDS`.
   Health check: `GET /health`. Hosts that inject `PORT` are supported.
5. **Deploy the dashboard** from `services/dashboard/Dockerfile` with
   `DASHBOARD_API_URL=https://<api-host>` and `DASHBOARD_API_KEY=<one of API_KEYS>`.
6. **Daily ingest (optional, needs an API-Football key):** add the secrets/variables listed in
   `.github/workflows/ingest-daily.yml` and set `INGEST_ENABLED=true`.

## Secrets checklist

Never commit: DB passwords, `API_KEYS`, `API_FOOTBALL_KEY`, `TARGET_DATABASE_URL`. They live in the
host's secret store and in GitHub Actions secrets. The API only ever connects as `api_reader`
(SELECT on `marts`, read-only transactions, 5 s statement timeout).

## Run the whole stack locally in containers

```bash
cp .env.example .env   # fill in passwords and API_KEYS
make up && make migrate
docker compose --profile app up --build   # API :8000, dashboard :8501
```
