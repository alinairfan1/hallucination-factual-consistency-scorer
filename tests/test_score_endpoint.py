from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from scorer.db.base import Base
from scorer.db.models import ScoringRun
from scorer.db.session import get_session
from scorer.main import app, get_llm_client


class FakeJudge:
    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self.calls: list[tuple[str, str]] = []

    def complete(self, system: str, user: str) -> str:
        self.calls.append((system, user))
        return self._responses.pop(0)


def _override_session(test_factory):
    def _get_session():
        session = test_factory()
        try:
            yield session
        finally:
            session.close()

    return _get_session


def test_score_endpoint_fully_supported_answer_returns_score_one():
    engine = create_engine(
        "sqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    test_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    fake_llm = FakeJudge(
        responses=[
            '["Paris is the capital of France."]',
            '{"verdict": "entailed", "reason": "Directly stated in the source."}',
        ]
    )

    app.dependency_overrides[get_session] = _override_session(test_factory)
    app.dependency_overrides[get_llm_client] = lambda: fake_llm

    try:
        client = TestClient(app)
        response = client.post(
            "/v1/score",
            json={
                "answer": "Paris is the capital of France.",
                "sources": ["Paris is the capital of France."],
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["score"] == 1.0
        assert body["flagged_claims"] == []

        with test_factory() as session:
            logged = session.query(ScoringRun).one()
            assert logged.answer == "Paris is the capital of France."
            assert logged.num_sources == 1
            assert logged.score == 1.0
            assert logged.num_flagged_claims == 0
            assert logged.sources == ["Paris is the capital of France."]
            assert logged.claims[0]["verdict"] == "entailed"
    finally:
        app.dependency_overrides.clear()


def test_score_endpoint_contradicted_claim_is_flagged():
    engine = create_engine(
        "sqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    test_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    fake_llm = FakeJudge(
        responses=[
            '["The Eiffel Tower is in Berlin."]',
            '{"verdict": "contradicted", "reason": "Sources say Paris, not Berlin."}',
        ]
    )

    app.dependency_overrides[get_session] = _override_session(test_factory)
    app.dependency_overrides[get_llm_client] = lambda: fake_llm

    try:
        client = TestClient(app)
        response = client.post(
            "/v1/score",
            json={
                "answer": "The Eiffel Tower is in Berlin.",
                "sources": ["The Eiffel Tower is in Paris."],
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["score"] == 0.0
        assert len(body["flagged_claims"]) == 1
        assert body["flagged_claims"][0]["verdict"] == "contradicted"

        with test_factory() as session:
            logged = session.query(ScoringRun).one()
            assert logged.score == 0.0
            assert logged.num_flagged_claims == 1
    finally:
        app.dependency_overrides.clear()


def test_score_endpoint_no_claims_extracted_logs_vacuous_score():
    engine = create_engine(
        "sqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    test_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    fake_llm = FakeJudge(responses=["[]"])

    app.dependency_overrides[get_session] = _override_session(test_factory)
    app.dependency_overrides[get_llm_client] = lambda: fake_llm

    try:
        client = TestClient(app)
        response = client.post(
            "/v1/score",
            json={"answer": "Hello!", "sources": ["irrelevant source"]},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["score"] == 1.0
        assert body["flagged_claims"] == []
    finally:
        app.dependency_overrides.clear()
