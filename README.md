# Football Analytics Platform

Work in progress. Ingests football data, models it in a warehouse, serves it through an API and
adds a predictive model. Full documentation will land with the final phase.

## Quick start

```bash
cp .env.example .env      # then set POSTGRES_PASSWORD
make venv                 # Python 3.12 venv via uv
make up                   # Postgres (pgvector) + Redis
make migrate              # create raw layer
make ingest-statsbomb     # World Cup 2022 into raw (idempotent)
make test
```

## Data attribution

Historical match data is provided by [StatsBomb](https://github.com/statsbomb/open-data)
(StatsBomb Open Data). Any analysis published from it must credit StatsBomb as the data source
and follow their [terms](https://github.com/statsbomb/open-data#terms--conditions).
