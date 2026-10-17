import numpy as np
import pandas as pd
import pytest

from football_ml.model import FEATURES, SymmetricModel, make_models, mirror


def test_probabilities_sum_to_one(synthetic):
    for name, model in make_models().items():
        fitted = model.fit(synthetic, synthetic.label.to_numpy())
        p = fitted.predict_proba(synthetic)
        assert p.shape == (len(synthetic), 3), name
        assert np.allclose(p.sum(axis=1), 1), name


def test_prediction_does_not_depend_on_home_away_labelling(synthetic):
    model = make_models()["full_logistic"].fit(synthetic, synthetic.label.to_numpy())
    X = synthetic.head(20)
    direct = model.predict_proba(X)
    swapped = model.predict_proba(mirror(X[FEATURES]))
    assert np.allclose(direct, swapped[:, ::-1], atol=1e-9)


def test_stronger_team_is_favoured(synthetic):
    model = make_models()["elo_logistic"].fit(synthetic, synthetic.label.to_numpy())
    strong_home = pd.DataFrame([{"elo_diff": 250.0, "abs_elo_diff": 250.0}])
    p = model.predict_proba(strong_home)[0]
    assert p[2] > p[1] and p[2] > p[0]


def test_class_missing_from_training_gets_zero_probability(synthetic):
    only_wins = synthetic[synthetic.label != 1]  # no draws at all
    model = make_models()["elo_logistic"].fit(only_wins, only_wins.label.to_numpy())
    p = model.predict_proba(synthetic.head(5))
    assert np.allclose(p.sum(axis=1), 1)


def test_mirror_flips_only_antisymmetric_features():
    X = pd.DataFrame(
        [{"elo_diff": 50.0, "abs_elo_diff": 50.0, "form_pts_diff": 1.0, "xgd_diff": 2.0}]
    )
    m = mirror(X).iloc[0]
    assert (m.elo_diff, m.abs_elo_diff, m.form_pts_diff, m.xgd_diff) == (-50.0, 50.0, -1.0, -2.0)


def test_baseline_predicts_class_prior(synthetic):
    base = make_models()["baseline_prior"].fit(synthetic, synthetic.label.to_numpy())
    p = base.predict_proba(synthetic.head(3))
    # Mirrored training makes the prior symmetric: P(home) == P(away).
    assert p[0, 0] == pytest.approx(p[0, 2])
    assert isinstance(base, SymmetricModel)
