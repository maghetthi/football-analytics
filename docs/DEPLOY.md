# Deployment guide

Production runs only the **serving layer**. The full local warehouse is ~835 MB (raw 188 MB,
staging 239 MB, marts 399 MB of which `fact_event` is 389 MB), but the API and the model read
~15 MB of marts. Free managed Postgres plans are small, so production receives a copy of those
tables instead of re-running the pipeline.

```
laptop:  StatsBomb -> raw -> dbt -> marts ──publish_marts.sh──► managed Postgres ◄── API ◄── dashboard
                                      └─ make train ─► models/ (committed) ──baked into──► API image
```

## Free plans, verified 2026-10-17

Read from each provider's own pages (and a live API key for API-Football). Re-check before you
commit; these change.

| Piece | Verified facts | Fit for this project |
|---|---|---|
| **Neon** (Postgres) | Free plan is permanent, no card. **1 GB** storage per project, 100 CU-hours, compute **suspends after 5 min idle** (cannot be disabled), pgvector included | Serving marts are ~15 MB. First query after idle pays a cold start. **Chosen** |
| **Upstash** (Redis) | Free: 500K commands/month, 250 MB, 10 GB bandwidth | ~2 commands per cached request, so ~250K requests/month. Cache fails open anyway. **Chosen** |
| **Render** web service | Free: 750 instance-hours/month per workspace, **spins down after 15 min idle, ~1 min cold start**; RAM/CPU not stated on the page | API idles at ~150 MiB (measured), so a small instance fits. **Chosen for the API** |
| Render Postgres | Free DB **expires after 30 days** (14 days grace, then deleted) | Rejected |
| Render Key Value | Free, but **not persisted** | Not needed (Upstash) |
| Fly.io | **No free tier** for new organizations; 2 h / 7 day trial; ~$2.19 per 30 days for a 256 MB machine | Not free |
| Railway | Trial: $5 one-time credit, expires in 30 days. Free plan: **$1 of credit per month**, 0.5 GB RAM per service | $1/month cannot keep a service running (my inference from the credit size) |
| Streamlit Community Cloud | Documented as free, public or private GitHub repos; **limits and sleep behaviour not on the page I could read** | Dashboard host; check "Status and limitations" when you deploy |
| API-Football | **Verified on your key:** Free = 100 requests/day, 10/minute, **seasons 2022-2024 only** | No current-season data; adapter enforces the daily budget |

Why two hosts: Render gives 750 free hours for the whole workspace, which is one service running
all month. The API and the dashboard would share it, so the dashboard goes to Streamlit Community
Cloud (it reads `services/dashboard/requirements.txt`).

Expect cold starts on the first visit (Render ~1 min, Neon a few seconds). Open the app before a
demo or recording to warm it up.

## Steps

1. **Create the database** in Neon. In Connection Details turn pooling off (direct connection).
2. **Store the connection locally**, never in chat or git:
   ```bash
   cp .env.neon.example .env.neon   # then fill it in; .env.neon is gitignored
   make neon-check                  # prints server, TLS, pgvector, role rights; no secrets
   ```
3. **Migrate** (schemas, `vector` extension, read-only `api_reader`, request log) and **publish
   the marts** from your local warehouse:
   ```bash
   make neon-migrate
   make neon-publish
   ```
4. **Redis (Upstash).** Create a free Redis database in the same AWS region as Neon (us-east-2) and
   copy its TLS URL, `rediss://default:<token>@<host>:6379`.
5. **Deploy the API on Render** with `render.yaml` (New > Blueprint > pick this repo). Render asks
   for the three secrets:

   | Variable | Value |
   |---|---|
   | `API_DB_PASSWORD` | the one in `.env.neon` (copy it with `grep ^API_DB_PASSWORD= .env.neon \| cut -d= -f2 \| pbcopy`) |
   | `API_KEYS` | a NEW production key: `openssl rand -hex 24 \| pbcopy`. Do not reuse your local one |
   | `REDIS_URL` | the Upstash `rediss://...` URL |

   The rest (`POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_SSLMODE=require`,
   `API_DB_USER=api_reader`, `CACHE_TTL_SECONDS`) is already in the blueprint. Health check:
   `GET /health`. Render injects `PORT`, which the image honours.
6. **Deploy the dashboard** on Streamlit Community Cloud (repo `maghetthi/football-analytics`, main
   file `services/dashboard/app.py`). Add secrets `DASHBOARD_API_URL` and `DASHBOARD_API_KEY`
   (one of the API's `API_KEYS`). Or use `services/dashboard/Dockerfile` on any container host.
7. **Daily ingest (optional, needs an API-Football key):** add the secrets/variables listed in
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
