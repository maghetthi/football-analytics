import numpy as np

from football_ml.evaluate import (
    expected_calibration_error,
    multiclass_brier,
    summarize,
    walk_forward,
)
from football_ml.model import make_models


def test_perfect_predictions_have_zero_brier():
    y = np.array([0, 1, 2])
    assert multiclass_brier(y, np.eye(3)[y]) == 0.0


def test_ece_is_zero_for_perfectly_confident_correct_predictions():
    y = np.array([2, 2, 0, 1])
    assert expected_calibration_error(y, np.eye(3)[y]) == 0.0


def test_overconfident_wrong_predictions_have_high_ece():
    y = np.array([0, 0, 0, 0])
    p = np.tile([0.0, 0.0, 1.0], (4, 1))
    assert expected_calibration_error(y, p) > 0.9


def test_summarize_reports_interval_around_log_loss():
    y = np.array([0, 1, 2, 2, 1, 0] * 10)
    p = np.full((len(y), 3), 1 / 3)
    s = summarize(y, p)
    assert s["log_loss"] == np.log(3) or abs(s["log_loss"] - np.log(3)) < 1e-9
    assert s["log_loss_ci_low"] <= s["log_loss"] <= s["log_loss_ci_high"]


def _flip_labels(df, tournament):
    out = df.copy()
    mask = out.tournament == tournament
    out.loc[mask, "label"] = 2 - out.loc[mask, "label"]
    return out


def test_walk_forward_never_peeks_at_the_future(synthetic):
    """Labels of a tournament may only influence folds that come AFTER it."""
    model = make_models()["full_logistic"]
    _, base = walk_forward(synthetic, model, min_train_tournaments=2)
    n_t2 = (synthetic.tournament == "T2").sum()

    # Last tournament is only ever a test set: flipping its labels changes no prediction.
    _, no_future = walk_forward(_flip_labels(synthetic, "T3"), model, min_train_tournaments=2)
    assert np.allclose(base, no_future)

    # T2 is test in fold 1 (unchanged) but training data for fold 2 (changed).
    _, t2_flipped = walk_forward(_flip_labels(synthetic, "T2"), model, min_train_tournaments=2)
    assert np.allclose(base[:n_t2], t2_flipped[:n_t2])
    assert not np.allclose(base[n_t2:], t2_flipped[n_t2:])
