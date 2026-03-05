from scorer.scoring import run_scoring


class FakeJudge:
    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)

    def complete(self, system: str, user: str) -> str:
        return self._responses.pop(0)


def test_run_scoring_fully_supported_answer_returns_score_one():
    llm = FakeJudge(
        responses=[
            '["Paris is the capital of France."]',
            '{"verdict": "entailed", "reason": "Directly stated in the source."}',
        ]
    )

    result = run_scoring(
        "Paris is the capital of France.", ["Paris is the capital of France."], llm
    )

    assert result.score == 1.0
    assert result.flagged_claims == []
    assert len(result.claims) == 1
    assert result.claims[0].verdict == "entailed"


def test_run_scoring_contradicted_claim_is_flagged():
    llm = FakeJudge(
        responses=[
            '["The Eiffel Tower is in Berlin."]',
            '{"verdict": "contradicted", "reason": "Sources say Paris, not Berlin."}',
        ]
    )

    result = run_scoring(
        "The Eiffel Tower is in Berlin.", ["The Eiffel Tower is in Paris."], llm
    )

    assert result.score == 0.0
    assert len(result.flagged_claims) == 1
    assert result.flagged_claims[0].verdict == "contradicted"


def test_run_scoring_no_claims_returns_vacuous_score():
    llm = FakeJudge(responses=["[]"])

    result = run_scoring("Hello!", ["irrelevant source"], llm)

    assert result.score == 1.0
    assert result.flagged_claims == []
