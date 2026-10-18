import numpy as np
import pandas as pd
import pytest

from football_ml.club_features import DEFAULT_PPM, build_club_features


def _fixtures(rows):
    cols = [
        "match_key",
        "home_club_key",
        "away_club_key",
        "is_finished",
        "home_goals",
        "away_goals",
        "result",
    ]
    df = pd.DataFrame(rows, columns=cols)
    df["kick_off_at"] = pd.date_range("2026-01-01", periods=len(df), freq="D", tz="UTC")
    df["competition_code"] = "UCL"
    df["season"] = 2025
    return df


def test_first_match_is_neutral_and_never_sees_its_own_result():
    out = build_club_features(_fixtures([("m1", "A", "B", True, 3, 0, "home_win")]))
    row = out.iloc[0]
    assert row.elo_diff == 0 and row.form_pts_diff == 0 and row.form_gd_diff == 0


def test_a_win_carries_into_the_next_match():
    out = build_club_features(
        _fixtures(
            [
                ("m1", "A", "B", True, 3, 0, "home_win"),
                ("m2", "A", "C", True, 1, 1, "draw"),
            ]
        )
    )
    row = out.iloc[1]
    assert row.elo_diff > 0
    assert row.form_pts_diff == pytest.approx(3.0 - DEFAULT_PPM)  # A won, C has no history
    assert row.form_gd_diff == pytest.approx(3.0)


def test_scheduled_match_sees_state_after_all_earlier_finished_matches_without_changing_it():
    out = build_club_features(
        _fixtures(
            [
                ("m1", "A", "B", True, 2, 0, "home_win"),
                ("m2", "A", "C", False, np.nan, np.nan, None),
                ("m3", "A", "D", False, np.nan, np.nan, None),
            ]
        )
    )
    # Two scheduled matches in a row: neither one alters A's rating for the other.
    assert out.iloc[1].elo_home == out.iloc[2].elo_home
    assert out.iloc[1].elo_home > 1500
    assert out.label.isna().tolist() == [False, True, True]


def test_labels_and_tournament_ids():
    out = build_club_features(_fixtures([("m1", "A", "B", True, 0, 2, "away_win")]))
    assert out.label.tolist() == [0]
    assert out.tournament.tolist() == ["UCL2025"]


def test_home_advantage_makes_a_home_win_move_ratings_less():
    from football_ml import elo

    plain = elo.update(1500, 1500, 1, 0)
    with_ha = elo.update(1500, 1500, 1, 0, home_advantage=60)
    assert with_ha[0] < plain[0]  # the home side gains less because it was favoured
