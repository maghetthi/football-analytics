from datetime import date

from pydantic import BaseModel


class Team(BaseModel):
    team_key: str
    team_name: str


class MatchSummary(BaseModel):
    match_key: str
    match_date: date
    stage_name: str | None
    home_team: str
    away_team: str
    home_score: int
    away_score: int
    result: str


class FormMatch(BaseModel):
    match_key: str
    match_date: date
    opponent: str
    is_home: bool
    goals_for: int
    goals_against: int
    result: str  # W / D / L from this team's point of view
    points: int
    xg_for: float
    xg_against: float


class FormSummary(BaseModel):
    matches: int
    wins: int
    draws: int
    losses: int
    points: int
    goals_for: int
    goals_against: int
    xg_for: float
    xg_against: float


class TeamForm(BaseModel):
    team_key: str
    team_name: str
    last: int
    summary: FormSummary
    matches: list[FormMatch]  # most recent first


class Shot(BaseModel):
    shot_key: str
    period: int
    minute: int
    second: int
    team_name: str
    player_name: str
    location_x: float | None
    location_y: float | None
    distance_to_goal: float | None
    shot_angle: float | None
    xg: float
    outcome: str
    is_goal: bool
    body_part: str | None
    shot_type: str | None
    is_penalty: bool
    is_shootout: bool


class MatchShots(BaseModel):
    match: MatchSummary
    total_xg_home: float
    total_xg_away: float
    shots: list[Shot]


class Player(BaseModel):
    player_key: str
    player_name: str
    country_name: str | None


class PlayerStats(BaseModel):
    player_key: str
    player_name: str
    appearances: int
    starts: int
    minutes_played: float
    shots: int
    goals: int
    penalty_goals: int
    xg: float
    np_xg: float
    goals_per_90: float | None
    np_xg_per_90: float | None
    goals_minus_xg: float


class PlayerComparison(BaseModel):
    competition_key: str | None
    season_key: str | None
    players: list[PlayerStats]  # same order as the request: a, b
