"""initial

Revision ID: 0001
Revises:
Create Date: 2026-07-26

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scoring_runs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("num_sources", sa.Integer(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("num_flagged_claims", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("scoring_runs")
