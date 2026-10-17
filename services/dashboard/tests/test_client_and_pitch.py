import httpx
import pytest

from football_dashboard.client import ApiClient, ApiError
from football_dashboard.pitch import shot_map


def _client(handler) -> ApiClient:
    return ApiClient("http://api", "k", httpx.Client(transport=httpx.MockTransport(handler)))


def test_sends_api_key_and_parses_json():
    def handler(request):
        assert request.headers["X-API-Key"] == "k"
        return httpx.Response(200, json=[{"team_key": "a", "team_name": "A"}])

    assert _client(handler).teams()[0]["team_name"] == "A"


def test_unauthorized_has_actionable_message():
    with pytest.raises(ApiError, match="DASHBOARD_API_KEY"):
        _client(lambda r: httpx.Response(401, json={"detail": "x"})).teams()


def test_api_errors_surface_the_detail():
    with pytest.raises(ApiError, match="404: Team not found"):
        _client(lambda r: httpx.Response(404, json={"detail": "Team not found"})).team_form("a")


def test_unreachable_api_is_an_apierror():
    def handler(request):
        raise httpx.ConnectError("down")

    with pytest.raises(ApiError, match="unreachable"):
        _client(handler).teams()


def test_all_matches_pages_until_a_short_page():
    pages = {0: [{"i": n} for n in range(100)], 100: [{"i": n} for n in range(100, 130)]}

    def handler(request):
        return httpx.Response(200, json=pages[int(request.url.params["offset"])])

    assert len(_client(handler).all_matches()) == 130


def test_shot_map_renders_with_goals_and_missing_locations():
    shots = [
        {"team_name": "A", "location_x": 100.0, "location_y": 40.0, "xg": 0.3, "is_goal": True},
        {"team_name": "B", "location_x": 95.0, "location_y": 30.0, "xg": 0.05, "is_goal": False},
        {"team_name": "B", "location_x": None, "location_y": None, "xg": 0.0, "is_goal": False},
    ]
    fig = shot_map(shots, "test")
    assert len(fig.axes) == 1


def test_default_timeout_tolerates_a_sleeping_free_host():
    client = ApiClient("http://api", "k")
    assert client._client.timeout.read >= 60
