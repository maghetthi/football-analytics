"""Endpoint tests against the real warehouse through the read-only role. Skipped if not built."""

import pytest


@pytest.fixture
def argentina(live_client, auth):
    teams = live_client.get("/teams", params={"q": "argentina"}, headers=auth).json()
    if not teams:
        pytest.skip("Argentina not in warehouse (ingest World Cup 2022 first)")
    return teams[0]["team_key"]


def test_team_search_is_case_insensitive_and_literal(live_client, auth):
    assert live_client.get("/teams", params={"q": "ARGEN"}, headers=auth).json()
    # '%' must be matched literally, not as a wildcard.
    assert live_client.get("/teams", params={"q": "%"}, headers=auth).json() == []


def test_form_returns_recent_matches_newest_first(live_client, auth, argentina):
    body = live_client.get(f"/teams/{argentina}/form", params={"last": 5}, headers=auth).json()
    dates = [m["match_date"] for m in body["matches"]]
    assert dates == sorted(dates, reverse=True)
    assert body["team_name"] == "Argentina"
    assert len(body["matches"]) == body["summary"]["matches"] <= 5


def test_form_summary_is_consistent_with_matches(live_client, auth, argentina):
    body = live_client.get(f"/teams/{argentina}/form", params={"last": 4}, headers=auth).json()
    s, ms = body["summary"], body["matches"]
    assert s["wins"] + s["draws"] + s["losses"] == len(ms)
    assert s["points"] == 3 * s["wins"] + s["draws"]
    assert s["goals_for"] == sum(m["goals_for"] for m in ms)


def test_unknown_team_is_404_and_not_cached(live_client, auth, cache):
    resp = live_client.get(f"/teams/{'0' * 32}/form", headers=auth)
    assert resp.status_code == 404
    assert cache.store == {}


def test_second_call_is_served_from_cache(live_client, auth, argentina, cache):
    first = live_client.get(f"/teams/{argentina}/form", headers=auth).json()
    assert len(cache.store) == 1
    assert live_client.get(f"/teams/{argentina}/form", headers=auth).json() == first


def test_match_shots_for_the_final(live_client, auth, argentina):
    matches = live_client.get("/matches", params={"team_key": argentina}, headers=auth).json()
    final = next(m for m in matches if m["stage_name"] == "Final")
    body = live_client.get(f"/matches/{final['match_key']}/shots", headers=auth).json()

    assert body["match"]["home_score"] == body["match"]["away_score"] == 3
    shots = body["shots"]
    assert all(0 <= s["xg"] <= 1 for s in shots)
    # Goals from open play + penalties in regulation/extra time equal the final score (3-3).
    in_play_goals = [s for s in shots if s["is_goal"] and not s["is_shootout"]]
    assert len(in_play_goals) == 6

    no_shootout = live_client.get(
        f"/matches/{final['match_key']}/shots", params={"include_shootout": False}, headers=auth
    ).json()
    assert not any(s["is_shootout"] for s in no_shootout["shots"])
    assert len(no_shootout["shots"]) < len(shots)


def test_unknown_match_is_404(live_client, auth):
    assert live_client.get(f"/matches/{'f' * 32}/shots", headers=auth).status_code == 404
