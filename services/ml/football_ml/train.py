"""CLI: python -m football_ml.train

Compares models with walk-forward validation, logs every run to MLflow, then refits the best
one on all data and writes the bundle + team state the API serves.
"""

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import mlflow  # noqa: E402
import numpy as np  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402

from football_ml.config import get_settings  # noqa: E402
from football_ml.evaluate import summarize, walk_forward  # noqa: E402
from football_ml.features import build_features, current_team_state, load_matches  # noqa: E402
from football_ml.model import ModelBundle, SymmetricModel, make_models  # noqa: E402
from football_ml.predict import BUNDLE_FILE, STATE_FILE  # noqa: E402

log = logging.getLogger("train")


def reliability_plot(y: np.ndarray, p: np.ndarray, path: Path, title: str) -> None:
    """Predicted confidence vs observed accuracy; the diagonal is perfect calibration."""
    conf, hit = p.max(axis=1), (p.argmax(axis=1) == y).astype(float)
    edges = np.quantile(conf, np.linspace(0, 1, 6))
    xs, ys = [], []
    for lo, hi in zip(edges[:-1], edges[1:], strict=True):
        mask = (conf >= lo) & (conf <= hi)
        if mask.any():
            xs.append(conf[mask].mean())
            ys.append(hit[mask].mean())
    fig, ax = plt.subplots(figsize=(4.5, 4.5))
    ax.plot([0, 1], [0, 1], "k--", label="perfect")
    ax.plot(xs, ys, "o-", label="model")
    ax.set(xlabel="predicted confidence", ylabel="observed accuracy", title=title)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    settings = get_settings()
    out = Path(settings.artifacts_dir)
    out.mkdir(parents=True, exist_ok=True)

    engine = create_engine(settings.database_url)
    df = build_features(load_matches(engine))
    log.info("%d matches, %d tournaments", len(df), df.tournament.nunique())

    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    mlflow.set_experiment("match-outcome")

    results: dict[str, tuple[dict, np.ndarray, np.ndarray]] = {}
    for name, model in make_models().items():
        y, p = walk_forward(df, model)
        metrics = summarize(y, p)
        results[name] = (metrics, y, p)
        with mlflow.start_run(run_name=name):
            mlflow.log_params(
                {
                    "model": name,
                    "features": ",".join(model.features),
                    "estimator": repr(model.estimator)[:250],
                    "validation": "walk_forward_by_tournament",
                    "n_matches_total": len(df),
                }
            )
            mlflow.log_metrics(metrics)
        log.info(
            "%-18s log_loss=%.4f brier=%.4f acc=%.3f ece=%.3f",
            name,
            *(metrics[k] for k in ("log_loss", "brier", "accuracy", "ece")),
        )

    best = min(results, key=lambda n: results[n][0]["log_loss"])
    base = results["baseline_prior"][0]["log_loss"]
    log.info("best: %s (log_loss %.4f vs baseline %.4f)", best, results[best][0]["log_loss"], base)

    metrics, y, p = results[best]
    plot_path = out / "calibration.png"
    reliability_plot(y, p, plot_path, f"{best}: walk-forward calibration")

    final = SymmetricModel(make_models()[best].estimator, make_models()[best].features)
    final.fit(df, df.label.to_numpy())

    bundle = ModelBundle(
        model=final,
        model_name=best,
        trained_at=datetime.now(UTC).isoformat(timespec="seconds"),
        data_cutoff=df.match_date.max().date().isoformat(),
        n_training_matches=len(df),
        metrics={k: metrics[k] for k in ("log_loss", "brier", "accuracy", "ece")},
    )
    joblib.dump(bundle, out / BUNDLE_FILE)

    state = current_team_state(engine, df)
    (out / STATE_FILE).write_text(json.dumps(state.to_dict(orient="records"), indent=1))

    with mlflow.start_run(run_name=f"final-{best}"):
        mlflow.log_params({"model": best, "trained_on": len(df), "stage": "final_fit"})
        mlflow.log_metrics({f"walk_forward_{k}": v for k, v in metrics.items()})
        mlflow.log_artifact(str(plot_path))
        mlflow.log_artifact(str(out / BUNDLE_FILE))
    log.info("saved %s and %s in %s", BUNDLE_FILE, STATE_FILE, out)


if __name__ == "__main__":
    main()
