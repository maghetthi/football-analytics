"""Features for scheduled club matches (UEFA competitions), from results only.

Walks the fixtures in kick-off order keeping an Elo rating and the last 5 results per club. Each
match's features are read BEFORE it is applied to the state, so a finished match never sees its own
result, and a scheduled match simply sees the state after every earlier finished match.
"""

from collections import deque

import numpy as np
import pandas as pd
from sqlalchemy import Engine, text

from football_ml import elo

HOME_ADVANTAGE = 60.0  # Elo points; the model also learns its own intercept
DEFAULT_PPM = 1.35  # points per match assumed for a club with no previous result
LABELS = {"away_win": 0, "draw": 1, "home_win": 2}

CLUB_FEATURES = ["elo_diff", "abs_elo_diff", "form_pts_diff", "form_gd_diff"]

FIXTURES_SQL = """
select match_key, competition_code, season, stage_name, kick_off_at,
       home_club_key, away_club_key, is_finished, home_goals, away_goals, result
from marts.fact_club_match
order by kick_off_at, match_key
"""


def load_fixtures(engine: Engine) -> pd.DataFrame:
    with engine.connect() as conn:
        df = pd.read_sql(text(FIXTURES_SQL), conn, parse_dates=["kick_off_at"])
    df["kick_off_at"] = pd.to_datetime(df["kick_off_at"], utc=True)
    return df


def _form(history: deque) -> tuple[float, float]:
    """(points per match, goal difference per match) over the stored results."""
    if not history:
        return DEFAULT_PPM, 0.0
    pts = sum(h[0] for h in history) / len(history)
    gd = sum(h[1] for h in history) / len(history)
    return pts, gd


def build_club_features(fixtures: pd.DataFrame) -> pd.DataFrame:
    df = fixtures.sort_values(["kick_off_at", "match_key"]).reset_index(drop=True)
    ratings: dict[str, float] = {}
    recent: dict[str, deque] = {}
    rows = []

    for r in df.itertuples():
        rh = ratings.get(r.home_club_key, elo.INITIAL_RATING)
        ra = ratings.get(r.away_club_key, elo.INITIAL_RATING)
        pts_h, gd_h = _form(recent.get(r.home_club_key, deque()))
        pts_a, gd_a = _form(recent.get(r.away_club_key, deque()))
        rows.append(
            {
                "elo_home": rh,
                "elo_away": ra,
                "elo_diff": rh - ra,
                "abs_elo_diff": abs(rh - ra),
                "form_pts_diff": pts_h - pts_a,
                "form_gd_diff": gd_h - gd_a,
                "history_home": len(recent.get(r.home_club_key, ())),
                "history_away": len(recent.get(r.away_club_key, ())),
            }
        )
        if r.is_finished and not (np.isnan(r.home_goals) or np.isnan(r.away_goals)):
            hg, ag = int(r.home_goals), int(r.away_goals)
            ratings[r.home_club_key], ratings[r.away_club_key] = elo.update(
                rh, ra, hg, ag, HOME_ADVANTAGE
            )
            for club, goals_for, goals_against in (
                (r.home_club_key, hg, ag),
                (r.away_club_key, ag, hg),
            ):
                points = 3 if goals_for > goals_against else 1 if goals_for == goals_against else 0
                recent.setdefault(club, deque(maxlen=5)).append((points, goals_for - goals_against))

    out = pd.concat([df, pd.DataFrame(rows)], axis=1)
    out["tournament"] = out.competition_code + out.season.astype(str)
    out["match_date"] = out.kick_off_at  # evaluate.walk_forward orders tournaments by this
    out["label"] = out.result.map(LABELS)
    return out
