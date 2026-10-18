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


def _player(live_client, auth, name):
    found = live_client.get("/players", params={"q": name}, headers=auth).json()
    if not found:
        pytest.skip(f"{name} not in warehouse")
    return found[0]["player_key"]


def test_compare_players_returns_both_in_request_order(live_client, auth):
    messi, mbappe = _player(live_client, auth, "Messi"), _player(live_client, auth, "Mbapp")
    body = live_client.get(
        "/players/compare", params={"a": messi, "b": mbappe}, headers=auth
    ).json()
    assert [p["player_key"] for p in body["players"]] == [messi, mbappe]
    for p in body["players"]:
        assert p["goals"] >= p["penalty_goals"] >= 0
        assert p["np_xg"] <= p["xg"] + 1e-6
        assert p["minutes_played"] > 0


def test_compare_same_player_is_422(live_client, auth):
    messi = _player(live_client, auth, "Messi")
    resp = live_client.get("/players/compare", params={"a": messi, "b": messi}, headers=auth)
    assert resp.status_code == 422


def test_compare_unknown_player_is_404(live_client, auth):
    messi = _player(live_client, auth, "Messi")
    resp = live_client.get("/players/compare", params={"a": messi, "b": "0" * 32}, headers=auth)
    assert resp.status_code == 404


# --- UEFA club fixtures (OpenLigaDB) ---


def _has_predictions(client, auth):
    rows = client.get(
        "/fixtures/upcoming", params={"limit": 100, "competition": "UCL"}, headers=auth
    )
    return [f for f in rows.json() if f["prediction"]] if rows.status_code == 200 else []


def test_upcoming_fixtures_are_ordered_and_scored(live_client, auth):
    scored = _has_predictions(live_client, auth)
    if not scored:
        pytest.skip(
            "no scored upcoming UCL fixtures (run ingest-openligadb, dbt-build, predict-clubs)"
        )
    dates = [f["kick_off_at"] for f in scored]
    assert dates == sorted(dates)
    for f in scored:
        p = f["prediction"]
        assert p["home_win"] + p["draw"] + p["away_win"] == pytest.approx(1, abs=1e-3)
        assert f["home_club"] != f["away_club"]
        assert f["competition_code"] == "UCL"


def test_upcoming_competition_filter(live_client, auth):
    rows = live_client.get("/fixtures/upcoming", params={"competition": "UEL"}, headers=auth).json()
    assert all(f["competition_code"] == "UEL" for f in rows)


def test_recent_results_have_scores_and_only_prior_predictions(live_client, auth):
    rows = live_client.get("/fixtures/recent", params={"limit": 20}, headers=auth).json()
    if not rows:
        pytest.skip("no finished UCL matches in the warehouse")
    for f in rows:
        assert f["result"] in {"home_win", "draw", "away_win"}
        if f["prediction"] is not None:
            # a prediction shown next to a result must have been made before kick-off
            assert f["prediction"]["predicted_at"] < f["kick_off_at"]
            assert isinstance(f["predicted_correctly"], bool)
        else:
            assert f["predicted_correctly"] is None


def test_track_record_is_consistent(live_client, auth):
    body = live_client.get("/fixtures/track-record", headers=auth).json()
    if body["scored_matches"] == 0:
        assert body["accuracy"] is None and body["log_loss"] is None
    else:
        assert 0 <= body["accuracy"] <= 1
        assert body["log_loss"] > 0
