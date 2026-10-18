from datetime import date, datetime

from pydantic import BaseModel, Field


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


class MatchPredictionRequest(BaseModel):
    home_team_key: str = Field(pattern=r"^[0-9a-f]{32}$")
    away_team_key: str = Field(pattern=r"^[0-9a-f]{32}$")


class Probabilities(BaseModel):
    home_win: float
    draw: float
    away_win: float


class ModelInfo(BaseModel):
    name: str
    trained_at: str
    data_cutoff: str
    training_matches: int
    walk_forward_log_loss: float


class MatchPrediction(BaseModel):
    home_team: str
    away_team: str
    probabilities: Probabilities
    features: dict[str, float]
    model: ModelInfo
    disclaimer: str


class ClubProbabilities(BaseModel):
    home_win: float
    draw: float
    away_win: float
    model_name: str
    predicted_at: datetime
    elo_home: float
    elo_away: float


class Fixture(BaseModel):
    match_key: str
    competition_code: str
    stage_name: str | None
    kick_off_at: datetime
    home_club: str
    away_club: str
    prediction: ClubProbabilities | None  # null until the daily job has scored the match


class FinishedFixture(Fixture):
    home_goals: int
    away_goals: int
    result: str
    predicted_correctly: bool | None  # null if no prediction was made before kick-off


class TrackRecord(BaseModel):
    scored_matches: int  # finished matches that had a prediction made BEFORE kick-off
    accuracy: float | None
    log_loss: float | None
    note: str
