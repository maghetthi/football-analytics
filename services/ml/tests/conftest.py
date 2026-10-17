import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def synthetic() -> pd.DataFrame:
    """4 tournaments x 40 matches; the outcome depends noisily on elo_diff."""
    rng = np.random.default_rng(42)
    rows = []
    for t in range(4):
        for i in range(40):
            elo_diff = rng.normal(0, 150)
            latent = elo_diff / 150 + rng.normal(0, 1)
            label = 2 if latent > 0.5 else 0 if latent < -0.5 else 1
            rows.append(
                {
                    "match_key": f"m{t}-{i}",
                    "tournament": f"T{t}",
                    "match_date": pd.Timestamp("2020-01-01") + pd.Timedelta(days=400 * t + i),
                    "elo_diff": elo_diff,
                    "abs_elo_diff": abs(elo_diff),
                    "form_pts_diff": rng.normal(0, 0.8),
                    "xgd_diff": rng.normal(0, 0.5),
                    "label": label,
                }
            )
    return pd.DataFrame(rows)
