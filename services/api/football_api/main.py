from fastapi import FastAPI

from football_api.routers import matches, players, teams

DESCRIPTION = """
Football analytics served from a PostgreSQL warehouse (dbt marts).

Historical data: [StatsBomb Open Data](https://github.com/statsbomb/open-data) (c) StatsBomb.
Any analysis published from it must credit StatsBomb as the data source.
Authenticate with the `X-API-Key` header.
"""

app = FastAPI(title="Football Analytics API", version="0.1.0", description=DESCRIPTION)
app.include_router(teams.router)
app.include_router(matches.router)
app.include_router(players.router)


@app.get("/health", tags=["meta"], summary="Liveness probe")
def health() -> dict[str, str]:
    return {"status": "ok"}
