"""Prefect flows. Plain functions underneath, so the CLI and tests can call them directly.

Run locally with an ephemeral Prefect engine (no server needed):
    python -m football_pipeline.flows statsbomb --competition 43 --season 106
    python -m football_pipeline.flows api-football --league 39 --season 2023 --days-back 3
"""

import argparse
import logging
from datetime import UTC, datetime, timedelta

from prefect import flow, get_run_logger, task
from sqlalchemy import create_engine

from football_pipeline.budget import RequestBudget
from football_pipeline.config import get_settings
from football_pipeline.ingest_statsbomb import run as run_statsbomb
from football_pipeline.raw import load_records
from football_pipeline.sources.api_football import ApiFootballAdapter


@task(retries=2, retry_delay_seconds=30)
def statsbomb_task(competition_id: int, season_id: int) -> tuple[int, int]:
    return run_statsbomb(competition_id, season_id)


@task(retries=1, retry_delay_seconds=60)
def api_football_task(league: int, season: int, date_from: str, date_to: str) -> tuple[int, int]:
    settings = get_settings()
    if settings.api_football_key is None:
        raise RuntimeError("API_FOOTBALL_KEY is not set")
    engine = create_engine(settings.database_url)
    budget = RequestBudget(engine, "api_football", settings.api_football_daily_budget)
    adapter = ApiFootballAdapter(settings.api_football_key.get_secret_value(), budget)
    inserted = skipped = 0
    for rec in adapter.fetch(league=league, season=season, date_from=date_from, date_to=date_to):
        with engine.begin() as conn:
            i, s = load_records(conn, [rec])
        inserted, skipped = inserted + i, skipped + s
    return inserted, skipped


@flow(name="statsbomb-ingest")
def statsbomb_flow(competition_id: int, season_id: int) -> tuple[int, int]:
    inserted, skipped = statsbomb_task(competition_id, season_id)
    get_run_logger().info("statsbomb: %d inserted, %d unchanged", inserted, skipped)
    return inserted, skipped


@flow(name="api-football-daily")
def api_football_daily_flow(league: int, season: int, days_back: int = 3) -> tuple[int, int]:
    """Re-reads a short trailing window so late score corrections are picked up (1 request)."""
    today = datetime.now(UTC).date()
    window = (today - timedelta(days=days_back)).isoformat(), today.isoformat()
    inserted, skipped = api_football_task(league, season, *window)
    get_run_logger().info("api-football %s..%s: %d new, %d same", *window, inserted, skipped)
    return inserted, skipped


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    sb = sub.add_parser("statsbomb")
    sb.add_argument("--competition", type=int, required=True)
    sb.add_argument("--season", type=int, required=True)
    af = sub.add_parser("api-football")
    af.add_argument("--league", type=int, required=True)
    af.add_argument("--season", type=int, required=True)
    af.add_argument("--days-back", type=int, default=3)
    args = parser.parse_args()

    if args.cmd == "statsbomb":
        statsbomb_flow(args.competition, args.season)
    else:
        api_football_daily_flow(args.league, args.season, args.days_back)


if __name__ == "__main__":
    main()
