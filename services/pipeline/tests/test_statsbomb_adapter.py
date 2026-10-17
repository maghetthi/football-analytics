import httpx

from football_pipeline.sources.statsbomb import StatsBombAdapter

FILES = {
    "/statsbomb/open-data/pin/data/competitions.json": [{"competition_id": 43}],
    "/statsbomb/open-data/pin/data/matches/43/106.json": [{"match_id": 1}, {"match_id": 2}],
    "/statsbomb/open-data/pin/data/lineups/1.json": [],
    "/statsbomb/open-data/pin/data/events/1.json": [{"id": "x"}],
    "/statsbomb/open-data/pin/data/lineups/2.json": [],
    "/statsbomb/open-data/pin/data/events/2.json": [{"id": "y"}],
}


def _client() -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        body = FILES.get(request.url.path)
        return httpx.Response(200, json=body) if body is not None else httpx.Response(404)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_fetch_yields_competitions_matches_then_per_match_files():
    adapter = StatsBombAdapter(ref="pin", client=_client())
    records = list(adapter.fetch(competition_id=43, season_id=106))

    assert [(r.resource, r.resource_key) for r in records] == [
        ("competitions", "all"),
        ("matches", "43/106"),
        ("lineups", "1"),
        ("events", "1"),
        ("lineups", "2"),
        ("events", "2"),
    ]
    assert all(r.source == "statsbomb" for r in records)
