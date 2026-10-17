import pytest

from football_pipeline import flows
from football_pipeline.config import Settings


def test_flows_are_registered_with_stable_names():
    assert flows.statsbomb_flow.name == "statsbomb-ingest"
    assert flows.api_football_flow.name == "api-football-ingest"


def test_retries_only_transient_failures():
    import httpx

    class State:
        def __init__(self, exc):
            self.exc = exc

        def result(self, raise_on_failure=True):
            return self.exc

    req = httpx.Request("GET", "http://x")
    server_error = httpx.HTTPStatusError(
        "x", request=req, response=httpx.Response(503, request=req)
    )
    client_error = httpx.HTTPStatusError(
        "x", request=req, response=httpx.Response(403, request=req)
    )
    retry = flows._retry_only_transient
    assert retry(None, None, State(httpx.ConnectError("down")))
    assert retry(None, None, State(server_error))
    assert not retry(None, None, State(client_error))
    assert not retry(None, None, State(RuntimeError("plan: no access to this season")))


def test_api_football_task_refuses_to_run_without_a_key(monkeypatch):
    settings = Settings(_env_file=None, postgres_user="u", postgres_password="p", postgres_db="d")
    monkeypatch.setattr(flows, "get_settings", lambda: settings)
    with pytest.raises(RuntimeError, match="API_FOOTBALL_KEY"):
        flows.api_football_task.fn(39, 2023, "2024-01-01", "2024-01-04")
