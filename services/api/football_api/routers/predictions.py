import logging
from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from football_api.auth import require_api_key
from football_api.schemas import MatchPrediction, MatchPredictionRequest
from football_api.settings import ApiSettings, get_settings
from football_ml.predict import Predictor

log = logging.getLogger(__name__)

router = APIRouter(
    prefix="/predictions", tags=["predictions"], dependencies=[Depends(require_api_key)]
)


@lru_cache
def _load(directory: str) -> Predictor:
    return Predictor.load(directory)


def get_predictor(settings: Annotated[ApiSettings, Depends(get_settings)]) -> Predictor:
    try:
        return _load(settings.artifacts_dir)
    except FileNotFoundError as exc:
        log.warning("model bundle not found in %s", settings.artifacts_dir)
        raise HTTPException(503, "Prediction model is not available; run `make train`") from exc


@router.post(
    "/match",
    response_model=MatchPrediction,
    summary="Win/draw/loss probabilities for a hypothetical match",
    description=(
        "Statistical estimate from Elo and recent form over international tournaments. "
        "Treat it as analysis, not betting advice. Home/away is nominal: swapping the teams "
        "swaps the probabilities."
    ),
)
def predict_match(
    body: MatchPredictionRequest, predictor: Annotated[Predictor, Depends(get_predictor)]
):
    if body.home_team_key == body.away_team_key:
        raise HTTPException(422, "Choose two different teams")
    try:
        return predictor.predict(body.home_team_key, body.away_team_key)
    except KeyError as exc:
        raise HTTPException(404, f"Team(s) not covered by the model: {exc.args[0]}") from exc
