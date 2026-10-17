from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy import Connection, text

from football_api.auth import require_api_key
from football_api.cache import Cache, get_cache
from football_api.db import get_conn
from football_api.schemas import MatchShots, MatchSummary, Shot

router = APIRouter(prefix="/matches", tags=["matches"], dependencies=[Depends(require_api_key)])

KEY_PATTERN = r"^[0-9a-f]{32}$"
MatchKey = Annotated[str, Path(pattern=KEY_PATTERN, description="Match key from GET /matches")]

MATCH_SELECT = """
    select m.match_key, m.match_date, m.stage_name, hm.team_name as home_team,
           aw.team_name as away_team, m.home_score, m.away_score, m.result,
           m.home_team_key, m.away_team_key
    from marts.fact_match m
    join marts.dim_team hm on hm.team_key = m.home_team_key
    join marts.dim_team aw on aw.team_key = m.away_team_key
"""


@router.get("", response_model=list[MatchSummary], summary="List matches")
def list_matches(
    conn: Annotated[Connection, Depends(get_conn)],
    team_key: Annotated[str | None, Query(pattern=KEY_PATTERN)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    rows = conn.execute(
        text(
            MATCH_SELECT
            + """
            where (cast(:team_key as text) is null
                   or m.home_team_key = :team_key or m.away_team_key = :team_key)
            order by m.match_date, m.match_key
            limit :limit offset :offset
            """
        ),
        {"team_key": team_key, "limit": limit, "offset": offset},
    )
    return [dict(r._mapping) for r in rows]


@router.get("/{match_key}/shots", response_model=MatchShots, summary="Shots with xG for a match")
def match_shots(
    match_key: MatchKey,
    conn: Annotated[Connection, Depends(get_conn)],
    cache: Annotated[Cache, Depends(get_cache)],
    include_shootout: Annotated[bool, Query(description="Include penalty-shootout kicks")] = True,
):
    cache_key = f"shots:v1:{match_key}:{int(include_shootout)}"
    if (hit := cache.get(cache_key)) is not None:
        return hit

    match = (
        conn.execute(text(MATCH_SELECT + " where m.match_key = :k"), {"k": match_key})
        .mappings()
        .first()
    )
    if match is None:
        raise HTTPException(404, "Match not found")

    rows = (
        conn.execute(
            text(
                """
                select s.shot_key, s.period, s.minute, s.second, t.team_name, p.player_name,
                       s.team_key, s.location_x, s.location_y, s.distance_to_goal, s.shot_angle,
                       s.xg, s.outcome, s.is_goal, s.body_part, s.shot_type, s.is_penalty,
                       s.is_shootout
                from marts.fact_shot s
                join marts.dim_team t on t.team_key = s.team_key
                join marts.dim_player p on p.player_key = s.player_key
                where s.match_key = :k and (:include_shootout or not s.is_shootout)
                order by s.period, s.minute, s.second, s.shot_key
                """
            ),
            {"k": match_key, "include_shootout": include_shootout},
        )
        .mappings()
        .all()
    )

    def xg_for(team_key: str) -> float:
        return round(sum(float(r["xg"]) for r in rows if r["team_key"] == team_key), 2)

    payload = MatchShots(
        match=MatchSummary(**match),
        total_xg_home=xg_for(match["home_team_key"]),
        total_xg_away=xg_for(match["away_team_key"]),
        shots=[Shot(**r) for r in rows],
    ).model_dump(mode="json")
    cache.set(cache_key, payload)
    return payload
