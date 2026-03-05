from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from scorer.benchmark import cli as cli_module
from scorer.benchmark.cli import build_judge, main
from scorer.config import settings
from scorer.db.base import Base
from scorer.db.models import BenchmarkRun


class FakeJudge:
    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)

    def complete(self, system: str, user: str) -> str:
        return self._responses.pop(0)


def test_build_judge_uses_configured_model_and_key(monkeypatch):
    class FakeClient:
        def __init__(self, api_key: str, retry_config, timeout_ms) -> None:
            self.api_key = api_key
            self.retry_config = retry_config
            self.timeout_ms = timeout_ms

    monkeypatch.setattr(cli_module, "Mistral", FakeClient)

    judge = build_judge()

    assert judge.model == settings.judge_model
    assert judge.client.api_key == settings.mistral_api_key
    assert judge.client.timeout_ms == cli_module.DEFAULT_JUDGE_TIMEOUT_MS


def test_main_prints_report_for_a_small_dataset(monkeypatch, tmp_path, capsys):
    dataset_path = tmp_path / "mini.jsonl"
    dataset_path.write_text(
        '{"answer": "Paris is the capital of France.", '
        '"sources": ["Paris is the capital of France."], "label": "supported"}\n'
        '{"answer": "Berlin is the capital of France.", '
        '"sources": ["Paris is the capital of France."], "label": "hallucinated"}\n'
    )

    fake_judge = FakeJudge(
        responses=[
            '["Paris is the capital of France."]',
            '{"verdict": "entailed", "reason": "ok"}',
            '["Berlin is the capital of France."]',
            '{"verdict": "contradicted", "reason": "no"}',
        ]
    )
    monkeypatch.setattr(cli_module, "build_judge", lambda: fake_judge)
    monkeypatch.setattr("sys.argv", ["scorer-benchmark", "--dataset", str(dataset_path)])

    engine = create_engine(
        "sqlite:///:memory:", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    test_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(cli_module, "build_session_factory", lambda: test_factory)

    main()

    captured = capsys.readouterr()
    assert "2 examples" in captured.out
    assert "Precision" in captured.out

    with test_factory() as session:
        persisted = session.query(BenchmarkRun).one()
        assert persisted.example_count == 2
        assert persisted.dataset_name == dataset_path.name
        assert len(persisted.examples) == 2
