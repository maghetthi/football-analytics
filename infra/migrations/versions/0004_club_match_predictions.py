"""predictions table for scheduled club matches (written by the ML job, read by the API)

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-17
"""

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Not a dbt model: dbt rebuilds its own tables, while predictions are an append-only history.
    # Each daily run adds a row per upcoming match, so we can later compare what the model said
    # BEFORE kickoff with what happened. ALTER DEFAULT PRIVILEGES (migration 0002) already gives
    # api_reader SELECT on new tables in this schema.
    op.execute(
        """
        CREATE TABLE marts.club_match_predictions (
            match_key     TEXT        NOT NULL,
            predicted_at  TIMESTAMPTZ NOT NULL,
            model_name    TEXT        NOT NULL,
            p_home_win    REAL        NOT NULL CHECK (p_home_win BETWEEN 0 AND 1),
            p_draw        REAL        NOT NULL CHECK (p_draw BETWEEN 0 AND 1),
            p_away_win    REAL        NOT NULL CHECK (p_away_win BETWEEN 0 AND 1),
            elo_home      REAL        NOT NULL,
            elo_away      REAL        NOT NULL,
            training_matches INT      NOT NULL,
            PRIMARY KEY (match_key, predicted_at),
            CONSTRAINT probabilities_sum_to_one
                CHECK (abs(p_home_win + p_draw + p_away_win - 1) < 0.001)
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_club_match_predictions_latest "
        "ON marts.club_match_predictions (match_key, predicted_at DESC)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS marts.club_match_predictions")
