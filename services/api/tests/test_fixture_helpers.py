from datetime import UTC, datetime

from football_api.routers.fixtures import _outcome, _prediction


def _row(h, d, a):
    return {
        "p_home_win": h,
        "p_draw": d,
        "p_away_win": a,
        "model_name": "m",
        "predicted_at": datetime(2026, 1, 1, tzinfo=UTC),
        "elo_home": 1600.04,
        "elo_away": 1500.0,
    }


def test_outcome_is_the_most_likely_result():
    assert _outcome(_row(0.2, 0.3, 0.5)) == "away_win"
    assert _outcome(_row(0.6, 0.2, 0.2)) == "home_win"
    assert _outcome(_row(0.3, 0.4, 0.3)) == "draw"


def test_unscored_match_has_no_prediction():
    assert _prediction(_row(None, None, None)) is None


def test_prediction_is_rounded_for_the_api():
    p = _prediction(_row(0.123456, 0.3, 0.576544))
    assert p["home_win"] == 0.1235 and p["elo_home"] == 1600.0
