"""Integration tests against the real Postgres (make up && make migrate). Skipped if unavailable.

Each test runs inside a transaction that is rolled back, so the DB is left untouched.
"""

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

from football_pipeline.config import get_settings
from football_pipeline.raw import RawRecord, load_records


@pytest.fixture
def conn():
    try:
        engine = create_engine(get_settings().database_url)
        connection = engine.connect()
        connection.execute(text("SELECT 1 FROM raw.source_payload LIMIT 1"))
    except Exception as exc:
        pytest.skip(f"database not ready: {type(exc).__name__}")
    connection.rollback()
    trans = connection.begin()
    yield connection
    trans.rollback()
    connection.close()


def _rec(payload):
    return RawRecord("test", "events", "999", payload, "http://example.test/x.json")


def _count(conn):
    query = text("SELECT count(*) FROM raw.source_payload WHERE source='test'")
    return conn.execute(query).scalar()


def test_reingesting_same_payload_is_noop(conn):
    assert load_records(conn, [_rec([{"a": 1}])]) == (1, 0)
    assert load_records(conn, [_rec([{"a": 1}])]) == (0, 1)
    assert _count(conn) == 1


def test_changed_payload_adds_new_version(conn):
    load_records(conn, [_rec([{"a": 1}])])
    assert load_records(conn, [_rec([{"a": 2}])]) == (1, 0)
    assert _count(conn) == 2


def test_raw_rows_cannot_be_updated_or_deleted(conn):
    load_records(conn, [_rec([{"a": 1}])])
    for stmt in (
        "UPDATE raw.source_payload SET payload='[]' WHERE source='test'",
        "DELETE FROM raw.source_payload WHERE source='test'",
    ):
        with pytest.raises(DBAPIError, match="immutable"), conn.begin_nested():
            conn.execute(text(stmt))
