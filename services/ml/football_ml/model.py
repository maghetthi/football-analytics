"""Model definitions. No MLflow/DB imports so the API can load a trained bundle cheaply."""

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, clone
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

# Class ids: 0 = away win, 1 = draw, 2 = home win.
CLASSES = ("away_win", "draw", "home_win")
FEATURES = ["elo_diff", "abs_elo_diff", "form_pts_diff", "xgd_diff"]
# Features that flip sign when home and away are swapped (abs_elo_diff does not).
ANTISYMMETRIC = ["elo_diff", "form_pts_diff", "xgd_diff"]


def mirror(X: pd.DataFrame) -> pd.DataFrame:
    flipped = X.copy()
    flipped[[c for c in ANTISYMMETRIC if c in flipped]] *= -1
    return flipped


class SymmetricModel:
    """Wraps any sklearn classifier so predictions do not depend on which team is called "home".

    In tournaments the home/away label is nominal (except for hosts), so we train on both
    orientations and average the prediction with its mirror image.
    """

    def __init__(self, estimator: BaseEstimator, features: list[str]) -> None:
        self.estimator = estimator
        self.features = features

    def fit(self, X: pd.DataFrame, y: np.ndarray) -> "SymmetricModel":
        X = X[self.features]
        X_aug = pd.concat([X, mirror(X)], ignore_index=True)
        y_aug = np.concatenate([y, 2 - y])  # swap away_win <-> home_win, draw stays
        self.model_ = clone(self.estimator).fit(X_aug, y_aug)
        return self

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        X = X[self.features]
        direct = self._proba(X)
        mirrored = self._proba(mirror(X))[:, ::-1]  # reverse class order back to this orientation
        return (direct + mirrored) / 2

    def _proba(self, X: pd.DataFrame) -> np.ndarray:
        raw = self.model_.predict_proba(X)
        out = np.zeros((len(X), 3))
        out[:, self.model_.classes_.astype(int)] = raw  # tolerate a class missing from training
        return out


class PlainModel:
    """Same interface as SymmetricModel, trained as-is: for fixtures with a real home advantage."""

    def __init__(self, estimator: BaseEstimator, features: list[str]) -> None:
        self.estimator = estimator
        self.features = features

    def fit(self, X: pd.DataFrame, y: np.ndarray) -> "PlainModel":
        self.model_ = clone(self.estimator).fit(X[self.features], y)
        return self

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        raw = self.model_.predict_proba(X[self.features])
        out = np.zeros((len(X), 3))
        out[:, self.model_.classes_.astype(int)] = raw
        return out


def make_models() -> dict[str, SymmetricModel]:
    """Candidates, from trivial to flexible. The point is to show what each step buys."""
    logistic = lambda c: make_pipeline(  # noqa: E731
        StandardScaler(), LogisticRegression(C=c, max_iter=1000)
    )
    return {
        "baseline_prior": SymmetricModel(DummyClassifier(strategy="prior"), FEATURES),
        "elo_logistic": SymmetricModel(logistic(1.0), ["elo_diff", "abs_elo_diff"]),
        "full_logistic": SymmetricModel(logistic(0.3), FEATURES),
        "gradient_boosting": SymmetricModel(
            HistGradientBoostingClassifier(max_depth=2, learning_rate=0.05, max_iter=80),
            FEATURES,
        ),
    }


@dataclass
class ModelBundle:
    """What gets saved to disk and loaded by the API."""

    model: SymmetricModel
    model_name: str
    trained_at: str
    data_cutoff: str
    n_training_matches: int
    metrics: dict[str, float]
