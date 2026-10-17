from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Connection, Engine, create_engine

from football_api.settings import get_settings


@lru_cache
def get_engine() -> Engine:
    return create_engine(get_settings().database_url, pool_pre_ping=True, pool_size=5)


def get_conn() -> Iterator[Connection]:
    """One connection per request; the role is read-only so no commit/rollback logic is needed."""
    with get_engine().connect() as conn:
        yield conn
