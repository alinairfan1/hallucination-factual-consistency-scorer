"""benchmark persistence and claim detail

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-27

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("scoring_runs", sa.Column("sources", sa.JSON(), nullable=True))
    op.add_column("scoring_runs", sa.Column("claims", sa.JSON(), nullable=True))

    op.create_table(
        "benchmark_runs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("dataset_name", sa.String(), nullable=False),
        sa.Column("judge_model", sa.String(), nullable=False),
        sa.Column("example_count", sa.Integer(), nullable=False),
        sa.Column("precision", sa.Float(), nullable=False),
        sa.Column("recall", sa.Float(), nullable=False),
        sa.Column("f1", sa.Float(), nullable=False),
        sa.Column("naive_always_supported_f1", sa.Float(), nullable=False),
        sa.Column("naive_length_heuristic_f1", sa.Float(), nullable=False),
        sa.Column("calibration", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "benchmark_example_results",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "benchmark_run_id", sa.String(), sa.ForeignKey("benchmark_runs.id"), nullable=False
        ),
        sa.Column("example_index", sa.Integer(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("sources", sa.JSON(), nullable=False),
        sa.Column("human_label", sa.String(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("claims", sa.JSON(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("benchmark_example_results")
    op.drop_table("benchmark_runs")
    op.drop_column("scoring_runs", "claims")
    op.drop_column("scoring_runs", "sources")
