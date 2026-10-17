from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy import Connection, text

from football_api.auth import require_api_key
from football_api.cache import Cache, get_cache
from football_api.db import get_conn
from football_api.schemas import FormMatch, FormSummary, Team, TeamForm

router = APIRouter(prefix="/teams", tags=["teams"], dependencies=[Depends(require_api_key)])

KEY_PATTERN = r"^[0-9a-f]{32}$"
TeamKey = Annotated[str, Path(pattern=KEY_PATTERN, description="Team key from GET /teams")]


def _like_pattern(q: str | None) -> str:
    """Escape LIKE wildcards so user input is matched literally."""
    escaped = (q or "").replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


@router.get("", response_model=list[Team], summary="Search teams by name")
def list_teams(
    conn: Annotated[Connection, Depends(get_conn)],
    q: Annotated[
        str | None, Query(max_length=60, description="Name contains (case-insensitive)")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
):
    rows = conn.execute(
        text(
            """
            select team_key, team_name from marts.dim_team
            where team_name ilike :pattern
            order by team_name limit :limit
            """
        ),
        {"pattern": _like_pattern(q), "limit": limit},
    )
    return [dict(r._mapping) for r in rows]


@router.get("/{team_key}/form", response_model=TeamForm, summary="Recent results and xG form")
def team_form(
    team_key: TeamKey,
    conn: Annotated[Connection, Depends(get_conn)],
    cache: Annotated[Cache, Depends(get_cache)],
    last: Annotated[int, Query(ge=1, le=20, description="Number of most recent matches")] = 5,
):
    cache_key = f"form:v1:{team_key}:{last}"
    if (hit := cache.get(cache_key)) is not None:
        return hit

    team = conn.execute(
        text("select team_name from marts.dim_team where team_key = :k"), {"k": team_key}
    ).scalar()
    if team is None:
        raise HTTPException(404, "Team not found")

    rows = (
        conn.execute(
            text(
                """
            select f.match_key, f.match_date, opp.team_name as opponent, f.is_home,
                   f.goals_for, f.goals_against, f.result, f.points,
                   round(f.xg_for::numeric, 2) as xg_for,
                   round(f.xg_against::numeric, 2) as xg_against
            from marts.mart_team_form f
            join marts.dim_team opp on opp.team_key = f.opponent_key
            where f.team_key = :k
            order by f.match_date desc, f.match_key
            limit :last
            """
            ),
            {"k": team_key, "last": last},
        )
        .mappings()
        .all()
    )

    matches = [FormMatch(**r) for r in rows]
    summary = FormSummary(
        matches=len(matches),
        wins=sum(m.result == "W" for m in matches),
        draws=sum(m.result == "D" for m in matches),
        losses=sum(m.result == "L" for m in matches),
        points=sum(m.points for m in matches),
        goals_for=sum(m.goals_for for m in matches),
        goals_against=sum(m.goals_against for m in matches),
        xg_for=round(sum(Decimal(str(m.xg_for)) for m in matches), 2),
        xg_against=round(sum(Decimal(str(m.xg_against)) for m in matches), 2),
    )
    payload = TeamForm(
        team_key=team_key, team_name=team, last=last, summary=summary, matches=matches
    ).model_dump(mode="json")
    cache.set(cache_key, payload)
    return payload
