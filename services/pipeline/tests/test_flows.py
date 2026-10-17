import pytest

from football_pipeline import flows
from football_pipeline.config import Settings


def test_flows_are_registered_with_stable_names():
    assert flows.statsbomb_flow.name == "statsbomb-ingest"
    assert flows.api_football_daily_flow.name == "api-football-daily"


def test_api_football_task_refuses_to_run_without_a_key(monkeypatch):
    settings = Settings(_env_file=None, postgres_user="u", postgres_password="p", postgres_db="d")
    monkeypatch.setattr(flows, "get_settings", lambda: settings)
    with pytest.raises(RuntimeError, match="API_FOOTBALL_KEY"):
        flows.api_football_task.fn(39, 2023, "2024-01-01", "2024-01-04")
