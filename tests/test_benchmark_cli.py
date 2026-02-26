from scorer.benchmark import cli as cli_module
from scorer.benchmark.cli import build_judge, main
from scorer.config import settings


class FakeJudge:
    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)

    def complete(self, system: str, user: str) -> str:
        return self._responses.pop(0)


def test_build_judge_uses_configured_model_and_key(monkeypatch):
    class FakeClient:
        def __init__(self, api_key: str) -> None:
            self.api_key = api_key

    monkeypatch.setattr(cli_module.anthropic, "Anthropic", FakeClient)

    judge = build_judge()

    assert judge.model == settings.judge_model
    assert judge.client.api_key == settings.anthropic_api_key


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

    main()

    captured = capsys.readouterr()
    assert "2 examples" in captured.out
    assert "Precision" in captured.out
