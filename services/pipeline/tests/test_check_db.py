import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

from football_pipeline.check_db import describe
from football_pipeline.config import get_settings


def test_describe_reports_server_without_credentials():
    engine = create_engine(get_settings().database_url)
    try:
        info = describe(engine)
    except OperationalError as exc:  # only "cannot connect" skips; real bugs must fail
        pytest.skip(f"database not ready: {type(exc).__name__}")
    assert info["server"].startswith("PostgreSQL")
    assert info["pgvector_available"]
    assert get_settings().postgres_password.get_secret_value() not in str(info)
