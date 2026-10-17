import pytest

VALID_KEY = "0" * 32


def test_health_is_public(client):
    assert client.get("/health").json() == {"status": "ok"}


@pytest.mark.parametrize("path", ["/teams", "/matches", f"/teams/{VALID_KEY}/form"])
def test_missing_key_is_401(client, no_db, path):
    resp = client.get(path)
    assert resp.status_code == 401
    assert resp.headers["www-authenticate"] == "ApiKey"


def test_wrong_key_is_401(client, no_db):
    assert client.get("/teams", headers={"X-API-Key": "nope"}).status_code == 401


def test_empty_configured_keys_reject_everything(client, no_db):
    from football_api.main import app
    from football_api.settings import ApiSettings, get_settings

    app.dependency_overrides[get_settings] = lambda: ApiSettings(
        _env_file=None, postgres_db="x", api_db_password="x", api_keys=""
    )
    assert client.get("/teams", headers={"X-API-Key": ""}).status_code == 401


@pytest.mark.parametrize(
    "path",
    [
        "/teams/not-a-key/form",
        f"/teams/{VALID_KEY}/form?last=0",
        f"/teams/{VALID_KEY}/form?last=21",
        "/teams?limit=0",
        "/teams?limit=101",
        "/matches?team_key=xyz",
        "/matches?offset=-1",
        "/matches/short/shots",
    ],
)
def test_invalid_input_is_422(client, no_db, auth, path):
    assert client.get(path, headers=auth).status_code == 422


def test_database_url_adds_sslmode_only_when_configured():
    from football_api.settings import ApiSettings

    base = {"_env_file": None, "postgres_db": "d", "api_db_password": "p"}
    assert "sslmode" not in str(ApiSettings(**base).database_url)
    assert ApiSettings(**base, postgres_sslmode="require").database_url.query == {
        "sslmode": "require"
    }
