import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from scorer.db.base import Base


class ScoringRun(Base):
    __tablename__ = "scoring_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    num_sources: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    num_flagged_claims: Mapped[int] = mapped_column(Integer, nullable=False)
    # Full claim-level detail backing the report viewer's live-history drill-down
    # (see PRODUCT.md's "Explicitly undecided" gap this closes). Nullable because
    # rows logged before this column existed have neither.
    sources: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    claims: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BenchmarkRun(Base):
    __tablename__ = "benchmark_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_name: Mapped[str] = mapped_column(String, nullable=False)
    judge_model: Mapped[str] = mapped_column(String, nullable=False)
    example_count: Mapped[int] = mapped_column(Integer, nullable=False)
    precision: Mapped[float] = mapped_column(Float, nullable=False)
    recall: Mapped[float] = mapped_column(Float, nullable=False)
    f1: Mapped[float] = mapped_column(Float, nullable=False)
    naive_always_supported_f1: Mapped[float] = mapped_column(Float, nullable=False)
    naive_length_heuristic_f1: Mapped[float] = mapped_column(Float, nullable=False)
    calibration: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    examples: Mapped[list["BenchmarkExampleResult"]] = relationship(
        back_populates="benchmark_run", order_by="BenchmarkExampleResult.example_index"
    )


class BenchmarkExampleResult(Base):
    __tablename__ = "benchmark_example_results"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    benchmark_run_id: Mapped[str] = mapped_column(ForeignKey("benchmark_runs.id"), nullable=False)
    example_index: Mapped[int] = mapped_column(Integer, nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    sources: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    human_label: Mapped[str] = mapped_column(String, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    claims: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)

    benchmark_run: Mapped["BenchmarkRun"] = relationship(back_populates="examples")
