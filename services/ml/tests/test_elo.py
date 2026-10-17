import pytest

from football_ml import elo


def test_equal_ratings_expect_half():
    assert elo.expected_score(1500, 1500) == pytest.approx(0.5)


def test_update_is_zero_sum_and_rewards_the_winner():
    h, a = elo.update(1500, 1500, 2, 0)
    assert h > 1500 > a
    assert h + a == pytest.approx(3000)


def test_draw_between_equals_changes_nothing():
    assert elo.update(1500, 1500, 1, 1) == (1500, 1500)


def test_upset_moves_ratings_more_than_expected_win():
    upset_gain = elo.update(1400, 1600, 1, 0)[0] - 1400
    expected_gain = elo.update(1600, 1400, 1, 0)[0] - 1600
    assert upset_gain > expected_gain


def test_bigger_margin_moves_more():
    assert elo.goal_multiplier(3) > elo.goal_multiplier(2) > elo.goal_multiplier(1) == 1.0


def test_pre_match_ratings_never_include_the_match_itself():
    pre, final = elo.pre_match_ratings([("A", "B", 3, 0), ("A", "C", 0, 0)])
    assert pre[0] == (elo.INITIAL_RATING, elo.INITIAL_RATING)  # nothing known yet
    assert pre[1][0] > elo.INITIAL_RATING  # A carries its first win into match 2
    assert pre[1][1] == elo.INITIAL_RATING  # C is new
    assert set(final) == {"A", "B", "C"}
