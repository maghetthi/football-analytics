"""Load a trained bundle and score a hypothetical match between two teams."""

import json
from datetime import date
from pathlib import Path

import joblib
import pandas as pd

from football_ml.model import CLASSES, ModelBundle

BUNDLE_FILE = "match_model.joblib"
STATE_FILE = "team_state.json"

DISCLAIMER = (
    "Statistical estimate from a small historical sample of international tournaments. "
    "It is not betting advice and carries substantial uncertainty."
)


class Predictor:
    def __init__(self, bundle: ModelBundle, team_state: list[dict]) -> None:
        self.bundle = bundle
        self.teams = {t["team_key"]: t for t in team_state}

    @classmethod
    def load(cls, directory: str | Path) -> "Predictor":
        d = Path(directory)
        bundle = joblib.load(d / BUNDLE_FILE)
        state = json.loads((d / STATE_FILE).read_text())
        return cls(bundle, state)

    def predict(self, home_key: str, away_key: str) -> dict:
        home, away = self.teams.get(home_key), self.teams.get(away_key)
        if home is None or away is None:
            missing = [k for k, t in ((home_key, home), (away_key, away)) if t is None]
            raise KeyError(missing)

        elo_diff = home["elo"] - away["elo"]
        row = pd.DataFrame(
            [
                {
                    "elo_diff": elo_diff,
                    "abs_elo_diff": abs(elo_diff),
                    "form_pts_diff": home["ppm"] - away["ppm"],
                    "xgd_diff": home["xgd_pm"] - away["xgd_pm"],
                }
            ]
        )
        proba = self.bundle.model.predict_proba(row)[0]
        return {
            "home_team": home["team_name"],
            "away_team": away["team_name"],
            "probabilities": dict(zip(CLASSES, (round(float(p), 4) for p in proba), strict=True)),
            "features": {k: round(float(v), 3) for k, v in row.iloc[0].items()},
            "model": {
                "name": self.bundle.model_name,
                "trained_at": self.bundle.trained_at,
                "data_cutoff": self.bundle.data_cutoff,
                "training_matches": self.bundle.n_training_matches,
                "walk_forward_log_loss": round(self.bundle.metrics["log_loss"], 4),
            },
            "disclaimer": DISCLAIMER,
        }


def today() -> str:
    return date.today().isoformat()
