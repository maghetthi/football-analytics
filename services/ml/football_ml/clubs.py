"""CLI: python -m football_ml.clubs [--dry-run]

Evaluates models on past UEFA club matches (walk-forward by competition-season), refits the best on
everything finished, predicts every scheduled match and appends the result to
marts.club_match_predictions. Each run adds rows (history), never overwrites them.
"""

import argparse
import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path

import matplotlib
import mlflow
import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sqlalchemy import create_engine, text

from football_ml.club_features import CLUB_FEATURES, build_club_features, load_fixtures
from football_ml.config import get_settings
from football_ml.evaluate import summarize, walk_forward
from football_ml.model import PlainModel
from football_ml.train import reliability_plot

matplotlib.use("Agg")
log = logging.getLogger("clubs")

# Predictions are only made for matches not played yet; very old "unfinished" rows are stale data.
SCHEDULED_WINDOW = timedelta(hours=3)


def make_club_models() -> dict[str, PlainModel]:
    logistic = lambda c: make_pipeline(  # noqa: E731
        StandardScaler(), LogisticRegression(C=c, max_iter=1000)
    )
    return {
        "baseline_prior": PlainModel(DummyClassifier(strategy="prior"), CLUB_FEATURES),
        "elo_logistic": PlainModel(logistic(1.0), ["elo_diff", "abs_elo_diff"]),
        "full_logistic": PlainModel(logistic(0.5), CLUB_FEATURES),
        "gradient_boosting": PlainModel(
            HistGradientBoostingClassifier(max_depth=2, learning_rate=0.05, max_iter=80),
            CLUB_FEATURES,
        ),
    }


def evaluate_models(played: pd.DataFrame) -> dict[str, tuple[dict, np.ndarray, np.ndarray]]:
    results = {}
    for name, model in make_club_models().items():
        # Skip the first seasons: Elo needs history before its signal means anything.
        y, p = walk_forward(played, model, min_train_tournaments=4)
        results[name] = (summarize(y, p), y, p)
        m = results[name][0]
        log.info(
            "%-18s log_loss=%.4f [%.3f-%.3f] brier=%.4f acc=%.3f ece=%.3f n=%d",
            name, m["log_loss"], m["log_loss_ci_low"], m["log_loss_ci_high"],
            m["brier"], m["accuracy"], m["ece"], m["n_test"],
        )  # fmt: skip
    return results


def scheduled_matches(df: pd.DataFrame, now: datetime) -> pd.DataFrame:
    return df[~df.is_finished & (df.kick_off_at >= pd.Timestamp(now - SCHEDULED_WINDOW))]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dry-run", action="store_true", help="evaluate and predict, write nothing"
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    settings = get_settings()

    read_engine = create_engine(settings.write_url if not args.dry_run else settings.database_url)
    df = build_club_features(load_fixtures(read_engine))
    played = df[df.is_finished & df.label.notna()].copy()
    played["label"] = played.label.astype(int)
    log.info(
        "%d finished matches, %d seasons/competitions",
        len(played), played.tournament.nunique(),
    )  # fmt: skip

    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    mlflow.set_experiment("club-outcome")
    results = evaluate_models(played)
    for name, (metrics, _, _) in results.items():
        with mlflow.start_run(run_name=name):
            mlflow.log_params({"model": name, "validation": "walk_forward_by_competition_season"})
            mlflow.log_metrics(metrics)

    best = min(results, key=lambda n: results[n][0]["log_loss"])
    base = results["baseline_prior"][0]["log_loss"]
    log.info("best: %s (log_loss %.4f vs baseline %.4f)", best, results[best][0]["log_loss"], base)

    out = Path(settings.artifacts_dir)
    out.mkdir(parents=True, exist_ok=True)
    reliability_plot(
        results[best][1], results[best][2], out / "club_calibration.png", f"{best}: clubs"
    )
    report = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "best_model": best,
        "finished_matches": int(len(played)),
        "walk_forward": {
            name: {k: round(v, 4) for k, v in metrics.items()}
            for name, (metrics, _, _) in results.items()
        },
    }
    (out / "club_report.json").write_text(json.dumps(report, indent=1) + "\n")

    final = make_club_models()[best].fit(played, played.label.to_numpy())
    now = datetime.now(UTC)
    todo = scheduled_matches(df, now)
    log.info("%d scheduled matches to predict", len(todo))
    if todo.empty:
        return

    proba = final.predict_proba(todo)
    rows = [
        {
            "match_key": r.match_key,
            "predicted_at": now,
            "model_name": best,
            "p_away": float(p[0]),
            "p_draw": float(p[1]),
            "p_home": float(p[2]),
            "elo_home": float(r.elo_home),
            "elo_away": float(r.elo_away),
            "n": int(len(played)),
        }
        for r, p in zip(todo.itertuples(), proba, strict=True)
    ]
    if args.dry_run:
        log.info(
            "dry run: not writing. First prediction: %s",
            {k: rows[0][k] for k in ("p_home", "p_draw", "p_away")},
        )
        return

    insert = text(
        """
        insert into marts.club_match_predictions
            (match_key, predicted_at, model_name, p_home_win, p_draw, p_away_win,
             elo_home, elo_away, training_matches)
        values (:match_key, :predicted_at, :model_name, :p_home, :p_draw, :p_away,
                :elo_home, :elo_away, :n)
        """
    )
    with read_engine.begin() as conn:
        conn.execute(insert, rows)
    log.info("wrote %d predictions", len(rows))


if __name__ == "__main__":
    main()
