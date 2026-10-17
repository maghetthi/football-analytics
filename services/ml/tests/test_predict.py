import pytest

from football_ml.model import ModelBundle, make_models
from football_ml.predict import Predictor

STATE = [
    {"team_key": "a" * 32, "team_name": "Strong", "elo": 1700.0, "ppm": 2.5, "xgd_pm": 1.0},
    {"team_key": "b" * 32, "team_name": "Weak", "elo": 1400.0, "ppm": 0.5, "xgd_pm": -1.0},
]


@pytest.fixture
def predictor(synthetic):
    model = make_models()["full_logistic"].fit(synthetic, synthetic.label.to_numpy())
    bundle = ModelBundle(
        model, "full_logistic", "2026-01-01T00:00:00", "2025-12-31", 160, {"log_loss": 1.0}
    )
    return Predictor(bundle, STATE)


def test_strong_team_gets_higher_win_probability(predictor):
    out = predictor.predict("a" * 32, "b" * 32)
    p = out["probabilities"]
    assert p["home_win"] > p["away_win"]
    assert sum(p.values()) == pytest.approx(1, abs=1e-3)
    assert "not betting advice" in out["disclaimer"]


def test_swapping_teams_swaps_probabilities(predictor):
    ab = predictor.predict("a" * 32, "b" * 32)["probabilities"]
    ba = predictor.predict("b" * 32, "a" * 32)["probabilities"]
    assert ab["home_win"] == pytest.approx(ba["away_win"], abs=1e-3)
    assert ab["draw"] == pytest.approx(ba["draw"], abs=1e-3)


def test_unknown_team_raises(predictor):
    with pytest.raises(KeyError):
        predictor.predict("a" * 32, "c" * 32)
