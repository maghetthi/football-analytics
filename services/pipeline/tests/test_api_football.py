import httpx
import pytest
from sqlalchemy import create_engine, text

from football_pipeline.budget import BudgetExceededError, RequestBudget
from football_pipeline.config import get_settings
from football_pipeline.sources.api_football import ApiFootballAdapter, ApiFootballError


@pytest.fixture
def engine():
    eng = create_engine(get_settings().database_url)
    try:
        with eng.connect() as conn:
            conn.execute(text("select 1 from raw.api_request_log limit 1"))
    except Exception as exc:
        pytest.skip(f"database not ready: {type(exc).__name__}")
    # Isolate from real usage: use a throwaway source name and clean up afterwards.
    yield eng
    with eng.begin() as conn:
        conn.execute(text("delete from raw.api_request_log where source = 'test_source'"))


def _adapter(engine, handler, limit=3):
    budget = RequestBudget(engine, "test_source", limit)
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return ApiFootballAdapter("secret", budget, client), budget


def _ok(request: httpx.Request) -> httpx.Response:
    return httpx.Response(
        200,
        json={"errors": [], "results": 1, "response": [{"fixture": {"id": 1}}]},
        headers={"x-ratelimit-requests-remaining": "42"},
    )


def test_fetch_yields_one_fixtures_record_and_sends_key(engine):
    seen = {}

    def handler(request):
        seen["key"] = request.headers["x-apisports-key"]
        seen["params"] = dict(request.url.params)
        return _ok(request)

    adapter, _ = _adapter(engine, handler)
    (rec,) = list(
        adapter.fetch(league=39, season=2023, date_from="2024-01-01", date_to="2024-01-04")
    )
    assert (rec.source, rec.resource, rec.resource_key) == (
        "api_football",
        "fixtures",
        "39/2023/2024-01-01_2024-01-04",
    )
    assert seen["key"] == "secret"
    assert seen["params"] == {
        "league": "39",
        "season": "2023",
        "from": "2024-01-01",
        "to": "2024-01-04",
    }


def test_every_request_is_counted_and_quota_header_recorded(engine):
    adapter, budget = _adapter(engine, _ok)
    list(adapter.fetch(league=1, season=2023, date_from="a", date_to="b"))
    assert budget.used_today() == 1
    with engine.connect() as conn:
        q = conn.execute(
            text("select quota_remaining from raw.api_request_log where source='test_source'")
        ).scalar()
    assert q == 42


def test_budget_blocks_requests_before_they_are_sent(engine):
    calls = []

    def handler(request):
        calls.append(request)
        return _ok(request)

    adapter, budget = _adapter(engine, handler, limit=2)
    for _ in range(2):
        list(adapter.fetch(league=1, season=2023, date_from="a", date_to="b"))
    with pytest.raises(BudgetExceededError):
        list(adapter.fetch(league=1, season=2023, date_from="a", date_to="b"))
    assert len(calls) == 2  # the third never left the process
    assert budget.remaining() == 0


def test_failed_requests_still_consume_budget(engine):
    adapter, budget = _adapter(engine, lambda r: httpx.Response(500))
    with pytest.raises(httpx.HTTPStatusError):
        list(adapter.fetch(league=1, season=2023, date_from="a", date_to="b"))
    assert budget.used_today() == 1


def test_errors_in_a_200_body_raise(engine):
    def handler(request):
        return httpx.Response(200, json={"errors": {"plan": "Free plans can't access this season"}})

    adapter, _ = _adapter(engine, handler)
    with pytest.raises(ApiFootballError, match="Free plans"):
        list(adapter.fetch(league=1, season=2025, date_from="a", date_to="b"))
