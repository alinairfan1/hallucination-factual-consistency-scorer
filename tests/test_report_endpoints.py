from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from scorer.db.base import Base
from scorer.db.models import BenchmarkExampleResult, BenchmarkRun, ScoringRun
from scorer.db.session import get_session
from scorer.main import app


def _make_test_session_factory():
    engine = create_engine(
        "sqlite:///:memory:", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def _override_session(test_factory):
    def _get_session():
        session = test_factory()
        try:
            yield session
        finally:
            session.close()

    return _get_session


def test_get_benchmark_returns_404_when_no_run_persisted():
    test_factory = _make_test_session_factory()
    app.dependency_overrides[get_session] = _override_session(test_factory)

    try:
        client = TestClient(app)
        response = client.get("/v1/benchmark")
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_get_benchmark_returns_latest_run_with_examples():
    test_factory = _make_test_session_factory()
    app.dependency_overrides[get_session] = _override_session(test_factory)

    try:
        with test_factory() as session:
            run = BenchmarkRun(
                dataset_name="HaluEval QA (100-example subset)",
                judge_model="mistral-large-latest",
                example_count=1,
                precision=87.0,
                recall=80.0,
                f1=83.3,
                naive_always_supported_f1=0.0,
                naive_length_heuristic_f1=73.7,
                calibration=[{"score": 1.0, "count": 54, "empiricalSupportedRate": 81.5}],
            )
            session.add(run)
            session.flush()
            session.add(
                BenchmarkExampleResult(
                    benchmark_run_id=run.id,
                    example_index=0,
                    question="What is the capital of France?",
                    answer="Paris",
                    sources=["Paris is the capital of France."],
                    human_label="supported",
                    score=1.0,
                    claims=[{"claim": "Paris is the capital of France.", "verdict": "entailed", "reason": "ok"}],
                )
            )
            session.commit()

        client = TestClient(app)
        response = client.get("/v1/benchmark")
        assert response.status_code == 200
        body = response.json()
        assert body["f1"] == 83.3
        assert body["naiveLengthHeuristicF1"] == 73.7
        assert len(body["examples"]) == 1
        assert body["examples"][0]["question"] == "What is the capital of France?"
        assert body["examples"][0]["claims"][0]["verdict"] == "entailed"
        assert body["calibration"][0]["empiricalSupportedRate"] == 81.5
    finally:
        app.dependency_overrides.clear()


def test_list_scoring_runs_returns_empty_list_when_none_logged():
    test_factory = _make_test_session_factory()
    app.dependency_overrides[get_session] = _override_session(test_factory)

    try:
        client = TestClient(app)
        response = client.get("/v1/scoring-runs")
        assert response.status_code == 200
        assert response.json() == []
    finally:
        app.dependency_overrides.clear()


def test_list_scoring_runs_returns_most_recent_first_with_claims():
    test_factory = _make_test_session_factory()
    app.dependency_overrides[get_session] = _override_session(test_factory)

    now = datetime.now(UTC)

    try:
        with test_factory() as session:
            # Explicit, distinct timestamps: SQLite's default CURRENT_TIMESTAMP has
            # only second resolution, so two rows created in the same test can tie
            # and make ordering nondeterministic (Postgres, used in production, has
            # microsecond resolution and doesn't have this issue).
            session.add(
                ScoringRun(
                    answer="first",
                    num_sources=1,
                    score=1.0,
                    num_flagged_claims=0,
                    sources=["s1"],
                    claims=[{"claim": "c1", "verdict": "entailed", "reason": "ok"}],
                    created_at=now,
                )
            )
            session.add(
                ScoringRun(
                    answer="second",
                    num_sources=1,
                    score=0.0,
                    num_flagged_claims=1,
                    sources=["s2"],
                    claims=[{"claim": "c2", "verdict": "contradicted", "reason": "no"}],
                    created_at=now + timedelta(seconds=1),
                )
            )
            session.commit()

        client = TestClient(app)
        response = client.get("/v1/scoring-runs")
        assert response.status_code == 200
        body = response.json()
        assert len(body) == 2
        assert body[0]["answer"] == "second"
        assert body[0]["claims"][0]["verdict"] == "contradicted"
        assert body[1]["answer"] == "first"
    finally:
        app.dependency_overrides.clear()


def test_list_scoring_runs_handles_legacy_rows_with_no_claims_or_sources():
    test_factory = _make_test_session_factory()
    app.dependency_overrides[get_session] = _override_session(test_factory)

    try:
        with test_factory() as session:
            session.add(
                ScoringRun(answer="legacy row", num_sources=1, score=1.0, num_flagged_claims=0)
            )
            session.commit()

        client = TestClient(app)
        response = client.get("/v1/scoring-runs")
        assert response.status_code == 200
        body = response.json()
        assert body[0]["sources"] == []
        assert body[0]["claims"] == []
    finally:
        app.dependency_overrides.clear()
