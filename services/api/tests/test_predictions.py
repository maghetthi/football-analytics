import numpy as np
import pandas as pd
import pytest

from football_api.main import app
from football_api.routers.predictions import get_predictor
from football_ml.model import ModelBundle, make_models
from football_ml.predict import Predictor

STRONG, WEAK = "a" * 32, "b" * 32
STATE = [
    {"team_key": STRONG, "team_name": "Strong", "elo": 1700.0, "ppm": 2.5, "xgd_pm": 1.0},
    {"team_key": WEAK, "team_name": "Weak", "elo": 1400.0, "ppm": 0.5, "xgd_pm": -1.0},
]


@pytest.fixture
def predictor_client(client):
    rng = np.random.default_rng(0)
    n = 200
    elo = rng.normal(0, 150, n)
    df = pd.DataFrame(
        {
            "elo_diff": elo,
            "abs_elo_diff": np.abs(elo),
            "form_pts_diff": rng.normal(0, 1, n),
            "xgd_diff": rng.normal(0, 1, n),
        }
    )
    y = np.where(elo + rng.normal(0, 100, n) > 40, 2, np.where(elo < -40, 0, 1))
    model = make_models()["full_logistic"].fit(df, y)
    bundle = ModelBundle(
        model, "full_logistic", "2026-01-01T00:00:00", "2025-12-31", n, {"log_loss": 0.9}
    )
    app.dependency_overrides[get_predictor] = lambda: Predictor(bundle, STATE)
    return client


def test_prediction_requires_api_key(predictor_client):
    body = {"home_team_key": STRONG, "away_team_key": WEAK}
    assert predictor_client.post("/predictions/match", json=body).status_code == 401


def test_prediction_returns_probabilities_and_disclaimer(predictor_client, auth):
    body = {"home_team_key": STRONG, "away_team_key": WEAK}
    resp = predictor_client.post("/predictions/match", json=body, headers=auth)
    assert resp.status_code == 200
    data = resp.json()
    p = data["probabilities"]
    assert sum(p.values()) == pytest.approx(1, abs=1e-3)
    assert p["home_win"] > p["away_win"]
    assert "not betting advice" in data["disclaimer"]
    assert data["model"]["name"] == "full_logistic"


def test_same_team_is_422(predictor_client, auth):
    body = {"home_team_key": STRONG, "away_team_key": STRONG}
    assert predictor_client.post("/predictions/match", json=body, headers=auth).status_code == 422


def test_unknown_team_is_404(predictor_client, auth):
    body = {"home_team_key": STRONG, "away_team_key": "c" * 32}
    assert predictor_client.post("/predictions/match", json=body, headers=auth).status_code == 404


def test_malformed_key_is_422(predictor_client, auth):
    body = {"home_team_key": "nope", "away_team_key": WEAK}
    assert predictor_client.post("/predictions/match", json=body, headers=auth).status_code == 422


def test_missing_model_is_503(client, auth, tmp_path):
    from football_api.settings import ApiSettings, get_settings

    app.dependency_overrides[get_settings] = lambda: ApiSettings(
        _env_file=None,
        postgres_db="x",
        api_db_password="x",
        api_keys="test-key-123",
        artifacts_dir=str(tmp_path),
    )
    body = {"home_team_key": STRONG, "away_team_key": WEAK}
    assert client.post("/predictions/match", json=body, headers=auth).status_code == 503
