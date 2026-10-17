"""raw layer: extensions, schema, immutable source_payload table

Revision ID: 0001
Revises:
Create Date: 2026-10-17
"""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE SCHEMA IF NOT EXISTS raw")

    # One row per (source, resource, key, content hash). Insert-only: a changed upstream
    # file becomes a NEW row (new hash), so history is kept and re-runs are no-ops.
    op.execute(
        """
        CREATE TABLE raw.source_payload (
            id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            source         TEXT        NOT NULL,   -- e.g. 'statsbomb', 'api_football'
            resource       TEXT        NOT NULL,   -- e.g. 'events', 'matches'
            resource_key   TEXT        NOT NULL,   -- e.g. match_id or '43/106'
            payload        JSONB       NOT NULL,
            payload_sha256 CHAR(64)    NOT NULL,   -- hash of canonical JSON
            source_url     TEXT        NOT NULL,
            ingested_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_source_payload_content
                UNIQUE (source, resource, resource_key, payload_sha256)
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_source_payload_lookup "
        "ON raw.source_payload (source, resource, resource_key, ingested_at DESC)"
    )

    # Enforce immutability in the database, not just by convention.
    op.execute(
        """
        CREATE FUNCTION raw.forbid_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'raw.% is immutable (% blocked)', TG_TABLE_NAME, TG_OP;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER source_payload_immutable
        BEFORE UPDATE OR DELETE ON raw.source_payload
        FOR EACH ROW EXECUTE FUNCTION raw.forbid_mutation()
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS raw.source_payload")
    op.execute("DROP FUNCTION IF EXISTS raw.forbid_mutation()")
    op.execute("DROP SCHEMA IF EXISTS raw")
