"""Thin HTTP client for the Football Analytics API. The dashboard never touches the database."""

import os

import httpx


class ApiError(RuntimeError):
    pass


class ApiClient:
    def __init__(self, base_url: str, api_key: str, client: httpx.Client | None = None) -> None:
        self._client = client or httpx.Client(timeout=15)
        self._base = base_url.rstrip("/")
        self._headers = {"X-API-Key": api_key}

    @classmethod
    def from_env(cls) -> "ApiClient":
        return cls(
            os.environ.get("DASHBOARD_API_URL", "http://localhost:8000"),
            os.environ.get("DASHBOARD_API_KEY", ""),
        )

    def _request(self, method: str, path: str, **kwargs):
        try:
            resp = self._client.request(
                method, f"{self._base}{path}", headers=self._headers, **kwargs
            )
        except httpx.HTTPError as exc:
            raise ApiError(f"API unreachable: {exc}") from exc
        if resp.status_code == 401:
            raise ApiError("The API rejected the key (set DASHBOARD_API_KEY).")
        if resp.status_code >= 400:
            detail = resp.json().get("detail", resp.text) if resp.content else resp.reason_phrase
            raise ApiError(f"{resp.status_code}: {detail}")
        return resp.json()

    def teams(self, q: str | None = None, limit: int = 100) -> list[dict]:
        return self._request("GET", "/teams", params={"q": q, "limit": limit})

    def team_form(self, team_key: str, last: int = 5) -> dict:
        return self._request("GET", f"/teams/{team_key}/form", params={"last": last})

    def all_matches(self) -> list[dict]:
        out: list[dict] = []
        while True:
            page = self._request("GET", "/matches", params={"limit": 100, "offset": len(out)})
            out += page
            if len(page) < 100:
                return out

    def match_shots(self, match_key: str, include_shootout: bool = False) -> dict:
        return self._request(
            "GET",
            f"/matches/{match_key}/shots",
            params={"include_shootout": str(include_shootout).lower()},
        )

    def players(self, q: str, limit: int = 20) -> list[dict]:
        return self._request("GET", "/players", params={"q": q, "limit": limit})

    def compare_players(self, a: str, b: str) -> dict:
        return self._request("GET", "/players/compare", params={"a": a, "b": b})

    def predict(self, home_team_key: str, away_team_key: str) -> dict:
        return self._request(
            "POST",
            "/predictions/match",
            json={"home_team_key": home_team_key, "away_team_key": away_team_key},
        )
