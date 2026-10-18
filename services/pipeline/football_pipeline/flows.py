"""Prefect flows. Plain functions underneath, so the CLI and tests can call them directly.

Run locally with an ephemeral Prefect engine (no server needed):
    python -m football_pipeline.flows statsbomb --competition 43 --season 106
    python -m football_pipeline.flows api-football --league 39 --season 2024
    python -m football_pipeline.flows openligadb [--current-only]
"""

import argparse
import logging
from datetime import UTC, datetime, timedelta

import httpx
from prefect import flow, get_run_logger, task
from sqlalchemy import create_engine

from football_pipeline.budget import RequestBudget
from football_pipeline.config import get_settings
from football_pipeline.ingest_statsbomb import run as run_statsbomb
from football_pipeline.raw import load_records
from football_pipeline.sources.api_football import ApiFootballAdapter
from football_pipeline.sources.openligadb import (
    CURRENT_SEASON,
    UEFA_CLUB_COMPETITIONS,
    OpenLigaDbAdapter,
)


@task(retries=2, retry_delay_seconds=30)
def statsbomb_task(competition_id: int, season_id: int) -> tuple[int, int]:
    return run_statsbomb(competition_id, season_id)


def _retry_only_transient(task, task_run, state) -> bool:
    """Retry network blips and 5xx. Never retry plan/season errors or an exhausted budget:
    they are deterministic and every retry would burn a request of the daily quota."""
    exc = state.result(raise_on_failure=False)
    if isinstance(exc, httpx.TransportError):
        return True
    return isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code >= 500


@task(retries=2, retry_delay_seconds=60, retry_condition_fn=_retry_only_transient)
def api_football_task(
    league: int, season: int, date_from: str | None = None, date_to: str | None = None
) -> tuple[int, int]:
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


@task(retries=2, retry_delay_seconds=30, retry_condition_fn=_retry_only_transient)
def openligadb_task(league: str, season: int) -> tuple[int, int]:
    engine = create_engine(get_settings().database_url)
    inserted = skipped = 0
    for rec in OpenLigaDbAdapter().fetch(league=league, season=season):
        with engine.begin() as conn:
            i, s = load_records(conn, [rec])
        inserted, skipped = inserted + i, skipped + s
    return inserted, skipped


@flow(name="statsbomb-ingest")
def statsbomb_flow(competition_id: int, season_id: int) -> tuple[int, int]:
    inserted, skipped = statsbomb_task(competition_id, season_id)
    get_run_logger().info("statsbomb: %d inserted, %d unchanged", inserted, skipped)
    return inserted, skipped


@flow(name="api-football-ingest")
def api_football_flow(league: int, season: int, days_back: int | None = None) -> tuple[int, int]:
    """1 request. With `days_back`, re-reads a trailing window (useful on plans that expose the
    current season); without it, the whole league season. Re-runs are no-ops if nothing changed."""
    window: tuple[str | None, str | None] = (None, None)
    if days_back is not None:
        today = datetime.now(UTC).date()
        window = (today - timedelta(days=days_back)).isoformat(), today.isoformat()
    inserted, skipped = api_football_task(league, season, *window)
    get_run_logger().info("api-football %s/%s: %d new, %d same", league, season, inserted, skipped)
    return inserted, skipped


@flow(name="openligadb-ingest")
def openligadb_flow(current_only: bool = False) -> tuple[int, int]:
    """Re-reads UEFA club competitions. `current_only` limits it to the live season (the daily job):
    finished results and newly scheduled fixtures arrive as new raw versions, history is untouched.
    """
    total_new = total_same = 0
    for league, season, _code in UEFA_CLUB_COMPETITIONS:
        if current_only and season != CURRENT_SEASON:
            continue
        new, same = openligadb_task(league, season)
        total_new, total_same = total_new + new, total_same + same
    get_run_logger().info("openligadb: %d new versions, %d unchanged", total_new, total_same)
    return total_new, total_same


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
    af.add_argument(
        "--days-back", type=int, default=None, help="trailing window; omit for the whole season"
    )
    ol = sub.add_parser("openligadb")
    ol.add_argument("--current-only", action="store_true")
    args = parser.parse_args()

    if args.cmd == "openligadb":
        openligadb_flow(args.current_only)
    elif args.cmd == "statsbomb":
        statsbomb_flow(args.competition, args.season)
    else:
        api_football_flow(args.league, args.season, args.days_back)


if __name__ == "__main__":
    main()
