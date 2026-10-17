import pandas as pd
import pytest

from football_ml.features import DEFAULT_PPM, build_features, per_match


def _matches() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "match_key": ["m1", "m2"],
            "match_date": pd.to_datetime(["2022-01-01", "2022-01-05"]),
            "home_team_key": ["A", "A"],
            "away_team_key": ["B", "C"],
            "home_score": [3, 1],
            "away_score": [0, 1],
            "result": ["home_win", "draw"],
            "tournament": ["T", "T"],
            "h_n": [0, 1],
            "h_pts": [None, 3.0],
            "h_xgf": [None, 2.0],
            "h_xga": [None, 0.5],
            "a_n": [0, 0],
            "a_pts": [None, None],
            "a_xgf": [None, None],
            "a_xga": [None, None],
        }
    )


def test_first_match_has_no_elo_edge_and_neutral_form():
    row = build_features(_matches()).iloc[0]
    assert row.elo_diff == 0
    assert row.form_pts_diff == 0  # both default to the same points-per-match
    assert row.xgd_diff == 0


def test_second_match_uses_ratings_from_before_it():
    row = build_features(_matches()).iloc[1]
    assert row.elo_diff > 0  # A won 3-0 earlier, C is a newcomer
    assert row.form_pts_diff == pytest.approx(3.0 - DEFAULT_PPM)
    assert row.xgd_diff == pytest.approx(1.5)


def test_labels_follow_result():
    assert build_features(_matches()).label.tolist() == [2, 1]


def test_per_match_fills_missing_history():
    out = per_match(pd.Series([None, 6.0]), pd.Series([0, 3]), fill=9.0)
    assert out.tolist() == [9.0, 2.0]
