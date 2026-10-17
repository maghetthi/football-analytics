"""Metrics and walk-forward evaluation. Walk-forward = train on the past, test on the next
tournament, so we never use future matches to predict earlier ones."""

import numpy as np
import pandas as pd
from sklearn.metrics import log_loss

from football_ml.model import SymmetricModel


def multiclass_brier(y: np.ndarray, p: np.ndarray) -> float:
    onehot = np.eye(p.shape[1])[y]
    return float(np.mean(np.sum((p - onehot) ** 2, axis=1)))


def expected_calibration_error(y: np.ndarray, p: np.ndarray, bins: int = 5) -> float:
    """Top-label ECE: |confidence - accuracy| averaged over confidence bins, weighted by size."""
    conf, pred = p.max(axis=1), p.argmax(axis=1)
    hit = (pred == y).astype(float)
    edges = np.linspace(conf.min(), conf.max() + 1e-9, bins + 1)
    ece = 0.0
    for lo, hi in zip(edges[:-1], edges[1:], strict=True):
        mask = (conf >= lo) & (conf < hi)
        if mask.any():
            ece += mask.mean() * abs(conf[mask].mean() - hit[mask].mean())
    return float(ece)


def bootstrap_logloss_ci(
    y: np.ndarray, p: np.ndarray, n: int = 1000, seed: int = 0
) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    losses = -np.log(np.clip(p[np.arange(len(y)), y], 1e-15, 1))
    boots = [rng.choice(losses, size=len(losses)).mean() for _ in range(n)]
    return float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))


def summarize(y: np.ndarray, p: np.ndarray) -> dict[str, float]:
    lo, hi = bootstrap_logloss_ci(y, p)
    return {
        "log_loss": float(log_loss(y, p, labels=[0, 1, 2])),
        "log_loss_ci_low": lo,
        "log_loss_ci_high": hi,
        "brier": multiclass_brier(y, p),
        "accuracy": float((p.argmax(axis=1) == y).mean()),
        "ece": expected_calibration_error(y, p),
        "n_test": float(len(y)),
    }


def walk_forward(
    df: pd.DataFrame, model: SymmetricModel, min_train_tournaments: int = 2
) -> tuple[np.ndarray, np.ndarray]:
    """Return pooled (y_true, probabilities) over every tournament after the first N."""
    order = df.groupby("tournament").match_date.min().sort_values().index.tolist()
    ys, ps = [], []
    for i in range(min_train_tournaments, len(order)):
        train = df[df.tournament.isin(order[:i])]
        test = df[df.tournament == order[i]]
        fitted = SymmetricModel(model.estimator, model.features).fit(train, train.label.to_numpy())
        ps.append(fitted.predict_proba(test))
        ys.append(test.label.to_numpy())
    return np.concatenate(ys), np.vstack(ps)
