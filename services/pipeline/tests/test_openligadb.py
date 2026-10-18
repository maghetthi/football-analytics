import httpx
import pytest

from football_pipeline.sources.openligadb import (
    CURRENT_SEASON,
    UEFA_CLUB_COMPETITIONS,
    OpenLigaDbAdapter,
)


def _adapter(handler) -> OpenLigaDbAdapter:
    return OpenLigaDbAdapter(httpx.Client(transport=httpx.MockTransport(handler)))


def test_fetch_yields_one_record_for_the_season():
    seen = {}

    def handler(request):
        seen["path"] = request.url.path
        return httpx.Response(200, json=[{"matchID": 1}, {"matchID": 2}])

    (rec,) = list(_adapter(handler).fetch(league="ucl", season=2026))
    assert seen["path"] == "/getmatchdata/ucl/2026"
    assert (rec.source, rec.resource, rec.resource_key) == ("openligadb", "matches", "ucl/2026")
    assert len(rec.payload) == 2


def test_http_errors_are_raised():
    with pytest.raises(httpx.HTTPStatusError):
        list(_adapter(lambda r: httpx.Response(503)).fetch(league="ucl", season=2026))


def test_non_list_payload_is_rejected():
    with pytest.raises(ValueError, match="unexpected OpenLigaDB payload"):
        list(
            _adapter(lambda r: httpx.Response(200, json={"error": "x"})).fetch(league="x", season=1)
        )


def test_competition_catalogue_is_consistent():
    keys = [(league, season) for league, season, _ in UEFA_CLUB_COMPETITIONS]
    assert len(keys) == len(set(keys)), "duplicate (league, season) entries"
    assert {code for *_, code in UEFA_CLUB_COMPETITIONS} == {"UCL", "UEL", "UECL"}
    assert any(season == CURRENT_SEASON for _, season, _ in UEFA_CLUB_COMPETITIONS)
