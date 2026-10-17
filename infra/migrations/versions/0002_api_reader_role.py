"""read-only role for the API: SELECT on marts only

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-17
"""

from alembic import op
from sqlalchemy import text

from football_pipeline.config import get_settings

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

ROLE = "api_reader"


def upgrade() -> None:
    password = get_settings().api_db_password
    if password is None:
        raise RuntimeError("API_DB_PASSWORD must be set to create the read-only API role")

    conn = op.get_bind()
    # dbt creates these schemas too (IF NOT EXISTS); the grants below need them to exist first.
    op.execute("CREATE SCHEMA IF NOT EXISTS staging")
    op.execute("CREATE SCHEMA IF NOT EXISTS marts")

    # DDL cannot take bind parameters, so pass the password through a transaction-local setting
    # and let format(%L) quote it inside the server: no string-building of secrets in Python.
    conn.execute(
        text("SELECT set_config('app.api_password', :pw, true)"),
        {"pw": password.get_secret_value()},
    )
    conn.execute(
        text(
            f"""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{ROLE}') THEN
                    EXECUTE format('CREATE ROLE {ROLE} LOGIN PASSWORD %L',
                                   current_setting('app.api_password'));
                ELSE
                    EXECUTE format('ALTER ROLE {ROLE} PASSWORD %L',
                                   current_setting('app.api_password'));
                END IF;
                EXECUTE format('GRANT CONNECT ON DATABASE %I TO {ROLE}', current_database());
            END
            $$
            """
        )
    )

    # Defence in depth: even a bug in the API cannot write, and runaway queries are cut off.
    op.execute(f"ALTER ROLE {ROLE} SET default_transaction_read_only = on")
    op.execute(f"ALTER ROLE {ROLE} SET statement_timeout = '5s'")

    op.execute(f"GRANT USAGE ON SCHEMA marts TO {ROLE}")
    op.execute(f"GRANT SELECT ON ALL TABLES IN SCHEMA marts TO {ROLE}")
    # dbt drops and recreates tables on every run; default privileges re-grant automatically.
    op.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA marts GRANT SELECT ON TABLES TO {ROLE}")


def downgrade() -> None:
    op.execute(f"DROP OWNED BY {ROLE}")
    op.execute(f"DROP ROLE IF EXISTS {ROLE}")
