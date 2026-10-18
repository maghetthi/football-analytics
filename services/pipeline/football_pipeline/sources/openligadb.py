"""OpenLigaDB adapter: community-maintained football results, no API key.

Data is licensed ODbL (https://www.openligadb.de): attribute OpenLigaDB when you publish results
derived from it. Entries are typed in by volunteers, so the catalogue contains test leagues and
several entries per competition; only the vetted ones in UEFA_CLUB_COMPETITIONS are ingested.
"""

from collections.abc import Iterator

import httpx

from football_pipeline.raw import RawRecord

BASE_URL = "https://api.openligadb.de"

# (league shortcut, season, competition code). Chosen after checking each entry is a complete
# competition with finished matches; seasons 2014 and 2019-2021 are not available in OpenLigaDB.
UEFA_CLUB_COMPETITIONS: list[tuple[str, int, str]] = [
    ("cl", 2013, "UCL"),
    ("cl", 2015, "UCL"),
    ("ucl2016", 2016, "UCL"),
    ("ucl2017", 2017, "UCL"),
    ("cl2018", 2018, "UCL"),
    ("uefacl22", 2022, "UCL"),
    ("champion1", 2023, "UCL"),
    ("ucl24", 2024, "UCL"),
    ("ucl", 2025, "UCL"),
    ("ucl", 2026, "UCL"),
    ("el1718", 2017, "UEL"),
    ("uel24", 2024, "UEL"),
    ("uel2026", 2026, "UEL"),
    ("uecl", 2022, "UECL"),
    ("uecl2026", 2026, "UECL"),
]
CURRENT_SEASON = 2026


class OpenLigaDbAdapter:
    name = "openligadb"

    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client or httpx.Client(
            timeout=30, transport=httpx.HTTPTransport(retries=3), follow_redirects=True
        )

    def fetch(self, *, league: str, season: int) -> Iterator[RawRecord]:
        """One request: every match (played or scheduled) of a league season."""
        url = f"{BASE_URL}/getmatchdata/{league}/{season}"
        resp = self._client.get(url)
        resp.raise_for_status()
        body = resp.json()
        if not isinstance(body, list):
            raise ValueError(f"unexpected OpenLigaDB payload for {league}/{season}: {type(body)}")
        yield RawRecord(self.name, "matches", f"{league}/{season}", body, url)
