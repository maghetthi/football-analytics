"""API-Football (api-sports.io) adapter, restricted to what the free plan allows.

Every call first checks the persisted daily budget and is logged whether it succeeds or not.
NOTE: written from the public docs without a live key. Header names and the fixtures payload
shape should be confirmed with the first real response (see docs in the repo README).
"""

from collections.abc import Iterator

import httpx

from football_pipeline.budget import RequestBudget
from football_pipeline.raw import RawRecord

BASE_URL = "https://v3.football.api-sports.io"


class ApiFootballError(RuntimeError):
    pass


class ApiFootballAdapter:
    name = "api_football"

    def __init__(
        self, api_key: str, budget: RequestBudget, client: httpx.Client | None = None
    ) -> None:
        self._budget = budget
        self._client = client or httpx.Client(timeout=30, headers={"x-apisports-key": api_key})
        if client is not None:
            self._client.headers["x-apisports-key"] = api_key

    def _get(self, path: str, params: dict) -> tuple[str, object]:
        self._budget.check()  # raises BudgetExceededError before spending a request
        status: int | None = None
        remaining: int | None = None
        try:
            resp = self._client.get(f"{BASE_URL}{path}", params=params)
            status = resp.status_code
            header = resp.headers.get("x-ratelimit-requests-remaining")
            remaining = int(header) if header and header.isdigit() else None
        finally:
            self._budget.record(path, params, status, remaining)
        resp.raise_for_status()
        body = resp.json()
        # The API answers HTTP 200 with an "errors" object (e.g. plan or season not allowed).
        if body.get("errors"):
            raise ApiFootballError(f"{path} {params}: {body['errors']}")
        return str(resp.url), body

    def fetch(
        self, *, league: int, season: int, date_from: str, date_to: str
    ) -> Iterator[RawRecord]:
        """One request: all fixtures (with scores) of a league/season in a date window."""
        params = {"league": league, "season": season, "from": date_from, "to": date_to}
        url, body = self._get("/fixtures", params)
        yield RawRecord(
            self.name, "fixtures", f"{league}/{season}/{date_from}_{date_to}", body, url
        )
