"""Elo ratings from match results. Pure functions: no I/O, easy to test."""

import math
from collections.abc import Iterable

INITIAL_RATING = 1500.0
K_FACTOR = 30.0


def expected_score(rating_a: float, rating_b: float) -> float:
    return 1.0 / (1.0 + 10 ** ((rating_b - rating_a) / 400.0))


def goal_multiplier(goal_diff: int) -> float:
    """Bigger wins move ratings more (World Football Elo convention)."""
    d = abs(goal_diff)
    if d <= 1:
        return 1.0
    if d == 2:
        return 1.5
    return (11 + d) / 8


def update(
    rating_home: float, rating_away: float, home_goals: int, away_goals: int
) -> tuple[float, float]:
    actual = 1.0 if home_goals > away_goals else 0.5 if home_goals == away_goals else 0.0
    delta = (
        K_FACTOR
        * goal_multiplier(home_goals - away_goals)
        * (actual - expected_score(rating_home, rating_away))
    )
    return rating_home + delta, rating_away - delta


def pre_match_ratings(
    matches: Iterable[tuple[str, str, int, int]],
) -> tuple[list[tuple[float, float]], dict[str, float]]:
    """matches: chronological (home_key, away_key, home_goals, away_goals).

    Returns the ratings each side had BEFORE its match (so no leakage) and the final ratings.
    """
    ratings: dict[str, float] = {}
    pre: list[tuple[float, float]] = []
    for home, away, hg, ag in matches:
        rh = ratings.get(home, INITIAL_RATING)
        ra = ratings.get(away, INITIAL_RATING)
        pre.append((rh, ra))
        ratings[home], ratings[away] = update(rh, ra, hg, ag)
    return pre, ratings


def is_finite(x: float) -> bool:
    return not (math.isnan(x) or math.isinf(x))
