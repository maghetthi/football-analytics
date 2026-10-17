import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from football_api.cache import MemoryCache, get_cache
from football_api.db import get_conn
from football_api.main import app
from football_api.settings import ApiSettings, get_settings

TEST_KEY = "test-key-123"


def _settings() -> ApiSettings:
    return ApiSettings(
        _env_file=None,
        postgres_db="unused",
        api_db_password="unused",
        api_keys=f"{TEST_KEY},other-key",
    )


@pytest.fixture
def cache() -> MemoryCache:
    return MemoryCache()


@pytest.fixture
def client(cache):
    """Client with fake settings and cache; get_conn is overridden per test module as needed."""
    app.dependency_overrides[get_settings] = _settings
    app.dependency_overrides[get_cache] = lambda: cache
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def auth() -> dict[str, str]:
    return {"X-API-Key": TEST_KEY}


@pytest.fixture
def no_db(client):
    """For tests that must be rejected before any query runs."""
    app.dependency_overrides[get_conn] = lambda: None


@pytest.fixture(scope="session")
def real_settings():
    try:
        return ApiSettings()
    except Exception as exc:
        pytest.skip(f"API settings not configured: {type(exc).__name__}")


@pytest.fixture(scope="session")
def db_engine(real_settings):
    """Engine for the read-only role; skips when the warehouse is not built."""
    engine = create_engine(real_settings.database_url)
    try:
        with engine.connect() as conn:
            conn.execute(text("select 1 from marts.fact_shot limit 1"))
    except Exception as exc:
        pytest.skip(f"warehouse not ready (migrate + ingest + dbt build): {type(exc).__name__}")
    return engine


@pytest.fixture
def live_client(client, db_engine):
    """Real read-only DB, fake cache and auth settings."""

    def real_conn():
        with db_engine.connect() as conn:
            yield conn

    app.dependency_overrides[get_conn] = real_conn
    return client
