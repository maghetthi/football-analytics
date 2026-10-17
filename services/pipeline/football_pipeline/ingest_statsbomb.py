"""CLI: python -m football_pipeline.ingest_statsbomb --competition 43 --season 106"""

import argparse
import logging

from sqlalchemy import create_engine

from football_pipeline.config import get_settings
from football_pipeline.raw import load_records
from football_pipeline.sources.statsbomb import StatsBombAdapter

log = logging.getLogger("ingest_statsbomb")


def run(competition_id: int, season_id: int) -> tuple[int, int]:
    settings = get_settings()
    adapter = StatsBombAdapter(ref=settings.statsbomb_ref)
    engine = create_engine(settings.database_url)

    inserted = skipped = 0
    # One transaction per record: a failure mid-run keeps everything loaded so far,
    # and the re-run skips it (idempotent) instead of starting over.
    for rec in adapter.fetch(competition_id=competition_id, season_id=season_id):
        with engine.begin() as conn:
            i, s = load_records(conn, [rec])
        inserted += i
        skipped += s
        log.info("%-12s %-8s %s", rec.resource, rec.resource_key, "inserted" if i else "unchanged")
    return inserted, skipped


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest StatsBomb open data into raw layer")
    parser.add_argument("--competition", type=int, required=True)
    parser.add_argument("--season", type=int, required=True)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    inserted, skipped = run(args.competition, args.season)
    log.info("done: %d inserted, %d unchanged", inserted, skipped)


if __name__ == "__main__":
    main()
