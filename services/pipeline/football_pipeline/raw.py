"""Loader for the immutable raw layer. Source-agnostic: adapters yield RawRecord."""

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from sqlalchemy import Column, MetaData, String, Table, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import Connection

metadata = MetaData(schema="raw")

source_payload = Table(
    "source_payload",
    metadata,
    Column("source", Text, nullable=False),
    Column("resource", Text, nullable=False),
    Column("resource_key", Text, nullable=False),
    Column("payload", JSONB, nullable=False),
    Column("payload_sha256", String(64), nullable=False),
    Column("source_url", Text, nullable=False),
)


@dataclass(frozen=True)
class RawRecord:
    source: str
    resource: str
    resource_key: str
    payload: Any  # parsed JSON, stored as received
    source_url: str


def content_hash(payload: Any) -> str:
    """SHA-256 of canonical JSON, so key order / whitespace changes don't create new versions."""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def load_records(conn: Connection, records: Iterable[RawRecord]) -> tuple[int, int]:
    """Insert records; returns (inserted, skipped). Idempotent via the content-hash unique key."""
    inserted = skipped = 0
    for rec in records:
        stmt = (
            pg_insert(source_payload)
            .values(
                source=rec.source,
                resource=rec.resource,
                resource_key=rec.resource_key,
                payload=rec.payload,
                payload_sha256=content_hash(rec.payload),
                source_url=rec.source_url,
            )
            .on_conflict_do_nothing(constraint="uq_source_payload_content")
            # RETURNING yields a row only on a real insert; rowcount is unreliable here.
            .returning(source_payload.c.payload_sha256)
        )
        if conn.execute(stmt).first() is not None:
            inserted += 1
        else:
            skipped += 1
    return inserted, skipped
