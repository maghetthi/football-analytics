"""StatsBomb Open Data adapter. Reads the public JSON files straight from GitHub.

Data (c) StatsBomb, released under their open data terms:
https://github.com/statsbomb/open-data - credit StatsBomb in anything published from it.
"""

from collections.abc import Iterator

import httpx

from football_pipeline.raw import RawRecord

BASE_URL = "https://raw.githubusercontent.com/statsbomb/open-data"


class StatsBombAdapter:
    name = "statsbomb"

    def __init__(self, ref: str = "master", client: httpx.Client | None = None) -> None:
        self._base = f"{BASE_URL}/{ref}/data"
        # transport retries cover connect errors only; HTTP errors surface via raise_for_status.
        self._client = client or httpx.Client(
            timeout=30, transport=httpx.HTTPTransport(retries=3), follow_redirects=True
        )

    def _get(self, path: str) -> tuple[str, object]:
        url = f"{self._base}/{path}"
        resp = self._client.get(url)
        resp.raise_for_status()
        return url, resp.json()

    def _record(self, resource: str, key: str, path: str) -> RawRecord:
        url, payload = self._get(path)
        return RawRecord(self.name, resource, key, payload, url)

    def fetch(self, *, competition_id: int, season_id: int) -> Iterator[RawRecord]:
        yield self._record("competitions", "all", "competitions.json")

        matches = self._record(
            "matches", f"{competition_id}/{season_id}", f"matches/{competition_id}/{season_id}.json"
        )
        yield matches

        for match in matches.payload:
            match_id = match["match_id"]
            yield self._record("lineups", str(match_id), f"lineups/{match_id}.json")
            yield self._record("events", str(match_id), f"events/{match_id}.json")
