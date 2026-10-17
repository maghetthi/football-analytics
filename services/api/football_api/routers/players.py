from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Connection, text

from football_api.auth import require_api_key
from football_api.cache import Cache, get_cache
from football_api.db import get_conn
from football_api.routers.teams import _like_pattern
from football_api.schemas import Player, PlayerComparison, PlayerStats

router = APIRouter(prefix="/players", tags=["players"], dependencies=[Depends(require_api_key)])

KEY_PATTERN = r"^[0-9a-f]{32}$"


@router.get("", response_model=list[Player], summary="Search players by name")
def list_players(
    conn: Annotated[Connection, Depends(get_conn)],
    q: Annotated[str | None, Query(max_length=60)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
):
    rows = conn.execute(
        text(
            """
            select player_key, player_name, country_name from marts.dim_player
            where player_name ilike :pattern or player_nickname ilike :pattern
            order by player_name limit :limit
            """
        ),
        {"pattern": _like_pattern(q), "limit": limit},
    )
    return [dict(r._mapping) for r in rows]


def _per_90(value: float, minutes: float) -> float | None:
    return round(value / minutes * 90, 3) if minutes > 0 else None


@router.get("/compare", response_model=PlayerComparison, summary="Compare two players' totals")
def compare_players(
    conn: Annotated[Connection, Depends(get_conn)],
    cache: Annotated[Cache, Depends(get_cache)],
    a: Annotated[str, Query(pattern=KEY_PATTERN, description="First player key")],
    b: Annotated[str, Query(pattern=KEY_PATTERN, description="Second player key")],
    competition_key: Annotated[str | None, Query(pattern=KEY_PATTERN)] = None,
    season_key: Annotated[str | None, Query(pattern=KEY_PATTERN)] = None,
):
    if a == b:
        raise HTTPException(422, "Choose two different players")

    cache_key = f"compare:v1:{a}:{b}:{competition_key}:{season_key}"
    if (hit := cache.get(cache_key)) is not None:
        return hit

    rows = (
        conn.execute(
            text(
                """
                select s.player_key, max(s.player_name) as player_name,
                       sum(s.appearances)::int as appearances, sum(s.starts)::int as starts,
                       sum(s.minutes_played)::float as minutes_played,
                       sum(s.shots)::int as shots, sum(s.goals)::int as goals,
                       sum(s.penalty_goals)::int as penalty_goals,
                       sum(s.xg)::float as xg, sum(s.np_xg)::float as np_xg
                from marts.mart_player_season_stats s
                where s.player_key in (:a, :b)
                  and (cast(:competition_key as text) is null
                       or s.competition_key = :competition_key)
                  and (cast(:season_key as text) is null or s.season_key = :season_key)
                group by s.player_key
                """
            ),
            {"a": a, "b": b, "competition_key": competition_key, "season_key": season_key},
        )
        .mappings()
        .all()
    )
    by_key = {r["player_key"]: r for r in rows}
    missing = [k for k in (a, b) if k not in by_key]
    if missing:
        raise HTTPException(404, f"No stats found for player(s): {', '.join(missing)}")

    def build(r) -> PlayerStats:
        return PlayerStats(
            **r,
            goals_per_90=_per_90(r["goals"], r["minutes_played"]),
            np_xg_per_90=_per_90(r["np_xg"], r["minutes_played"]),
            goals_minus_xg=round(r["goals"] - r["xg"], 3),
        )

    payload = PlayerComparison(
        competition_key=competition_key,
        season_key=season_key,
        players=[build(by_key[a]), build(by_key[b])],
    ).model_dump(mode="json")
    cache.set(cache_key, payload)
    return payload
