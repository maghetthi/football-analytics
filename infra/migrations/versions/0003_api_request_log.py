"""request log used to enforce the daily budget of rate-limited sources

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-17
"""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Mutable on purpose (unlike raw.source_payload): it is bookkeeping, not source data.
    op.execute(
        """
        CREATE TABLE raw.api_request_log (
            id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            source          TEXT        NOT NULL,
            requested_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
            endpoint        TEXT        NOT NULL,
            params          JSONB       NOT NULL DEFAULT '{}',
            status_code     INT,
            quota_remaining INT          -- from the provider's response headers, when sent
        )
        """
    )
    op.execute("CREATE INDEX ix_api_request_log_day ON raw.api_request_log (source, requested_at)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS raw.api_request_log")
