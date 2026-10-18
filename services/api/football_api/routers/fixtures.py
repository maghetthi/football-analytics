from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Connection, text

from football_api.auth import require_api_key
from football_api.cache import Cache, get_cache
from football_api.db import get_conn
from football_api.schemas import FinishedFixture, Fixture, TrackRecord

router = APIRouter(prefix="/fixtures", tags=["fixtures"], dependencies=[Depends(require_api_key)])

Competition = Literal["UCL", "UEL", "UECL"]

# Latest prediction for a match. For finished matches only predictions made before kick-off count,
# otherwise the model would be "predicting" a result it could already see.
LATEST_PREDICTION = """
    left join lateral (
        select p.p_home_win, p.p_draw, p.p_away_win, p.model_name, p.predicted_at,
               p.elo_home, p.elo_away
        from marts.club_match_predictions p
        where p.match_key = m.match_key {before_kick_off}
        order by p.predicted_at desc limit 1
    ) p on true
"""

BASE = """
    select m.match_key, m.competition_code, m.stage_name, m.kick_off_at,
           hc.club_name as home_club, ac.club_name as away_club,
           m.home_goals, m.away_goals, m.result,
           p.p_home_win, p.p_draw, p.p_away_win, p.model_name, p.predicted_at,
           p.elo_home, p.elo_away
    from marts.fact_club_match m
    join marts.dim_club hc on hc.club_key = m.home_club_key
    join marts.dim_club ac on ac.club_key = m.away_club_key
"""


def _prediction(row) -> dict | None:
    if row["p_home_win"] is None:
        return None
    return {
        "home_win": round(float(row["p_home_win"]), 4),
        "draw": round(float(row["p_draw"]), 4),
        "away_win": round(float(row["p_away_win"]), 4),
        "model_name": row["model_name"],
        "predicted_at": row["predicted_at"],
        "elo_home": round(float(row["elo_home"]), 1),
        "elo_away": round(float(row["elo_away"]), 1),
    }


def _outcome(row) -> str:
    return max(
        (("home_win", row["p_home_win"]), ("draw", row["p_draw"]), ("away_win", row["p_away_win"])),
        key=lambda kv: kv[1],
    )[0]


@router.get(
    "/upcoming",
    response_model=list[Fixture],
    summary="Scheduled UEFA club matches with model probabilities",
    description=(
        "Matches not yet played, soonest first, scored by a model built from results only (Elo "
        "and recent form). Statistical estimate, not betting advice. Source: OpenLigaDB (ODbL)."
    ),
)
def upcoming(
    conn: Annotated[Connection, Depends(get_conn)],
    cache: Annotated[Cache, Depends(get_cache)],
    competition: Annotated[Competition | None, Query()] = "UCL",
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
):
    cache_key = f"fixtures:upcoming:v1:{competition}:{limit}"
    if (hit := cache.get(cache_key)) is not None:
        return hit

    rows = (
        conn.execute(
            text(
                BASE
                + LATEST_PREDICTION.format(before_kick_off="")
                + """
                where not m.is_finished
                  and m.kick_off_at >= now() - interval '3 hours'
                  and (cast(:competition as text) is null or m.competition_code = :competition)
                order by m.kick_off_at, m.match_key
                limit :limit
                """
            ),
            {"competition": competition, "limit": limit},
        )
        .mappings()
        .all()
    )
    payload = [
        Fixture(
            **{k: r[k] for k in Fixture.model_fields if k != "prediction"},
            prediction=_prediction(r),
        ).model_dump(mode="json")
        for r in rows
    ]
    cache.set(cache_key, payload)
    return payload


@router.get(
    "/recent",
    response_model=list[FinishedFixture],
    summary="Latest finished matches, with what the model said before kick-off",
)
def recent(
    conn: Annotated[Connection, Depends(get_conn)],
    competition: Annotated[Competition | None, Query()] = "UCL",
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    rows = (
        conn.execute(
            text(
                BASE
                + LATEST_PREDICTION.format(before_kick_off="and p.predicted_at < m.kick_off_at")
                + """
                where m.is_finished
                  and (cast(:competition as text) is null or m.competition_code = :competition)
                order by m.kick_off_at desc, m.match_key
                limit :limit
                """
            ),
            {"competition": competition, "limit": limit},
        )
        .mappings()
        .all()
    )
    out = []
    for r in rows:
        pred = _prediction(r)
        out.append(
            FinishedFixture(
                match_key=r["match_key"],
                competition_code=r["competition_code"],
                stage_name=r["stage_name"],
                kick_off_at=r["kick_off_at"],
                home_club=r["home_club"],
                away_club=r["away_club"],
                prediction=pred,
                home_goals=r["home_goals"],
                away_goals=r["away_goals"],
                result=r["result"],
                predicted_correctly=None if pred is None else _outcome(r) == r["result"],
            )
        )
    return out


@router.get(
    "/track-record",
    response_model=TrackRecord,
    summary="How the model did on matches it predicted BEFORE they were played",
)
def track_record(
    conn: Annotated[Connection, Depends(get_conn)],
    competition: Annotated[Competition | None, Query()] = "UCL",
):
    row = (
        conn.execute(
            text(
                """
                with scored as (
                    select case m.result
                               when 'home_win' then p.p_home_win
                               when 'draw' then p.p_draw
                               else p.p_away_win
                           end as p_actual,
                           greatest(p.p_home_win, p.p_draw, p.p_away_win) as p_max
                    from marts.fact_club_match m
                    join lateral (
                        select * from marts.club_match_predictions q
                        where q.match_key = m.match_key and q.predicted_at < m.kick_off_at
                        order by q.predicted_at desc limit 1
                    ) p on true
                    where m.is_finished
                      and (cast(:competition as text) is null or m.competition_code = :competition)
                )
                select count(*) as n,
                       avg((p_actual >= p_max)::int) as accuracy,
                       avg(-ln(greatest(p_actual, 1e-6))) as log_loss
                from scored
                """
            ),
            {"competition": competition},
        )
        .mappings()
        .one()
    )
    n = int(row["n"])
    return TrackRecord(
        scored_matches=n,
        accuracy=None if n == 0 else round(float(row["accuracy"]), 3),
        log_loss=None if n == 0 else round(float(row["log_loss"]), 3),
        note=(
            "Only matches predicted before kick-off count. It starts empty and grows as scheduled "
            "matches are played; a uniform guess scores log-loss 1.099."
        ),
    )
