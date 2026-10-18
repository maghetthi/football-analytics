"""Build the match-level feature table from the warehouse marts (pre-match information only)."""

import numpy as np
import pandas as pd
from sqlalchemy import Engine, text

from football_ml import elo

MATCHES_SQL = """
select m.match_key, m.match_date, m.home_team_key, m.away_team_key,
       m.home_score, m.away_score, m.result,
       c.competition_name || ' ' || s.season_name as tournament,
       hf.matches_in_window as h_n, hf.points_last5 as h_pts,
       hf.xg_for_last5 as h_xgf, hf.xg_against_last5 as h_xga,
       af.matches_in_window as a_n, af.points_last5 as a_pts,
       af.xg_for_last5 as a_xgf, af.xg_against_last5 as a_xga
from marts.fact_match m
join marts.dim_competition c using (competition_key)
join marts.dim_season s using (season_key)
join marts.mart_team_form hf on hf.match_key = m.match_key and hf.team_key = m.home_team_key
join marts.mart_team_form af on af.match_key = m.match_key and af.team_key = m.away_team_key
where c.is_international  -- club leagues have a real home advantage; this model assumes none
order by m.match_date, m.match_key
"""

# Used when a team has no previous match in the data (typical points per match in tournaments).
DEFAULT_PPM = 1.35
LABELS = {"away_win": 0, "draw": 1, "home_win": 2}


def load_matches(engine: Engine) -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql(text(MATCHES_SQL), conn, parse_dates=["match_date"])


def per_match(total: pd.Series, n: pd.Series, fill: float) -> pd.Series:
    """Rolling totals over the last <=5 matches -> per-match average; fill when no history."""
    return (total.astype(float) / n.replace(0, np.nan)).fillna(fill)


def build_features(matches: pd.DataFrame) -> pd.DataFrame:
    """Add Elo and form-difference features. Input must be chronological."""
    df = matches.sort_values(["match_date", "match_key"]).reset_index(drop=True)

    pre, _ = elo.pre_match_ratings(
        zip(df.home_team_key, df.away_team_key, df.home_score, df.away_score, strict=True)
    )
    df["elo_home"] = [p[0] for p in pre]
    df["elo_away"] = [p[1] for p in pre]
    df["elo_diff"] = df.elo_home - df.elo_away
    df["abs_elo_diff"] = df.elo_diff.abs()

    df["form_pts_diff"] = per_match(df.h_pts, df.h_n, DEFAULT_PPM) - per_match(
        df.a_pts, df.a_n, DEFAULT_PPM
    )
    h_xgd = per_match(df.h_xgf - df.h_xga, df.h_n, 0.0)
    a_xgd = per_match(df.a_xgf - df.a_xga, df.a_n, 0.0)
    df["xgd_diff"] = h_xgd - a_xgd

    df["label"] = df.result.map(LABELS).astype(int)
    return df


def current_team_state(engine: Engine, matches_with_features: pd.DataFrame) -> pd.DataFrame:
    """Per-team state going into the NEXT match: final Elo + form over the last 5 played."""
    final = elo.pre_match_ratings(
        zip(
            matches_with_features.home_team_key,
            matches_with_features.away_team_key,
            matches_with_features.home_score,
            matches_with_features.away_score,
            strict=True,
        )
    )[1]
    sql = """
        select f.team_key, t.team_name, f.match_date, f.points, f.xg_for, f.xg_against
        from marts.mart_team_form f join marts.dim_team t using (team_key)
    """
    with engine.connect() as conn:
        tm = pd.read_sql(text(sql), conn, parse_dates=["match_date"])
    last5 = tm.sort_values("match_date").groupby("team_key").tail(5)
    agg = last5.groupby(["team_key", "team_name"]).agg(
        n=("points", "size"),
        pts=("points", "sum"),
        xgf=("xg_for", "sum"),
        xga=("xg_against", "sum"),
    )
    agg = agg.reset_index()
    agg["ppm"] = agg.pts / agg.n
    agg["xgd_pm"] = (agg.xgf - agg.xga) / agg.n
    agg = agg[agg.team_key.isin(final)]  # only teams the international model has actually seen
    agg["elo"] = agg.team_key.map(final)
    return agg[["team_key", "team_name", "elo", "ppm", "xgd_pm", "n"]]
