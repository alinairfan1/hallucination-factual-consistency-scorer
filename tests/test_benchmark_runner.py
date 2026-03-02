from scorer.benchmark.runner import QueryResult, run_benchmark
from scorer.dataset import DatasetExample


class FakeJudge:
    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)

    def complete(self, system: str, user: str) -> str:
        return self._responses.pop(0)


def test_run_benchmark_produces_one_result_per_example():
    examples = [
        DatasetExample(answer="a1", sources=["s1"], label="supported"),
        DatasetExample(answer="a2", sources=["s2"], label="hallucinated"),
    ]
    llm = FakeJudge(
        responses=[
            '["claim1"]',
            '{"verdict": "entailed", "reason": "ok"}',
            '["claim2"]',
            '{"verdict": "contradicted", "reason": "no"}',
        ]
    )

    results = run_benchmark(examples, llm)

    assert len(results) == 2
    assert all(isinstance(r, QueryResult) for r in results)


def test_run_benchmark_predicts_supported_when_score_meets_threshold():
    examples = [DatasetExample(answer="a1", sources=["s1"], label="supported")]
    llm = FakeJudge(responses=['["claim1"]', '{"verdict": "entailed", "reason": "ok"}'])

    results = run_benchmark(examples, llm, threshold=1.0)

    assert results[0].predicted_label == "supported"
    assert results[0].score == 1.0
    assert results[0].actual_label == "supported"


def test_run_benchmark_predicts_hallucinated_when_score_below_threshold():
    examples = [DatasetExample(answer="a1", sources=["s1"], label="hallucinated")]
    llm = FakeJudge(responses=['["claim1"]', '{"verdict": "contradicted", "reason": "no"}'])

    results = run_benchmark(examples, llm, threshold=1.0)

    assert results[0].predicted_label == "hallucinated"
    assert results[0].score == 0.0
    assert results[0].num_flagged_claims == 1


def test_run_benchmark_continues_past_a_malformed_judge_response():
    examples = [
        DatasetExample(answer="a1", sources=["s1"], label="supported"),
        DatasetExample(answer="a2", sources=["s2"], label="hallucinated"),
        DatasetExample(answer="a3", sources=["s3"], label="supported"),
    ]
    llm = FakeJudge(
        responses=[
            '["claim1"]',
            '{"verdict": "entailed", "reason": "ok"}',
            "not valid json",  # claim extraction for example 2 blows up
            '["claim3"]',
            '{"verdict": "entailed", "reason": "ok"}',
        ]
    )

    results = run_benchmark(examples, llm)

    assert len(results) == 3
    assert results[0].error is None
    assert results[0].predicted_label == "supported"
    assert results[1].error is not None
    assert results[1].predicted_label == "hallucinated"
    assert results[1].actual_label == "hallucinated"
    assert results[2].error is None
    assert results[2].predicted_label == "supported"


def test_run_benchmark_preserves_example_order_via_index():
    examples = [
        DatasetExample(answer="a1", sources=["s1"], label="supported"),
        DatasetExample(answer="a2", sources=["s2"], label="supported"),
    ]
    llm = FakeJudge(
        responses=[
            '["c1"]',
            '{"verdict": "entailed", "reason": "ok"}',
            '["c2"]',
            '{"verdict": "entailed", "reason": "ok"}',
        ]
    )

    results = run_benchmark(examples, llm)

    assert [r.index for r in results] == [0, 1]
