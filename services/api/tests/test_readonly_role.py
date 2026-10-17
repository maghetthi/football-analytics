"""The API role must be physically unable to read raw data or write anything."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError


def test_can_read_marts(db_engine):
    with db_engine.connect() as conn:
        assert conn.execute(text("select count(*) from marts.fact_match")).scalar() > 0


@pytest.mark.parametrize(
    "sql",
    [
        "select * from raw.source_payload limit 1",
        "select * from staging.stg_statsbomb__matches limit 1",
        "insert into marts.dim_team (team_key, source_team_id, team_name) values ('x', 0, 'x')",
        "delete from marts.dim_team",
        "create table marts.evil (id int)",
        "drop table marts.dim_team",
    ],
)
def test_forbidden_statements_are_rejected(db_engine, sql):
    with pytest.raises(DBAPIError), db_engine.connect() as conn:
        conn.execute(text(sql))
