import pytest

from scorer.entailment import check_entailment


class FakeJudge:
    def __init__(self, response_text: str) -> None:
        self.response_text = response_text
        self.last_system: str | None = None
        self.last_user: str | None = None

    def complete(self, system: str, user: str) -> str:
        self.last_system = system
        self.last_user = user
        return self.response_text


def test_check_entailment_returns_entailed_verdict_and_reason():
    llm = FakeJudge('{"verdict": "entailed", "reason": "Directly stated in the source."}')

    verdict, reason = check_entailment(
        "Paris is the capital of France.",
        ["Paris is the capital of France."],
        llm,
    )

    assert verdict == "entailed"
    assert reason == "Directly stated in the source."


def test_check_entailment_returns_contradicted_verdict():
    llm = FakeJudge('{"verdict": "contradicted", "reason": "Sources say Paris, not Berlin."}')

    verdict, reason = check_entailment(
        "The Eiffel Tower is in Berlin.",
        ["The Eiffel Tower is in Paris."],
        llm,
    )

    assert verdict == "contradicted"


def test_check_entailment_returns_not_enough_info_verdict():
    llm = FakeJudge('{"verdict": "not_enough_info", "reason": "Sources do not mention height."}')

    verdict, reason = check_entailment(
        "The tower is 330 meters tall.",
        ["The tower is located in Paris."],
        llm,
    )

    assert verdict == "not_enough_info"


def test_check_entailment_includes_claim_and_sources_in_user_message():
    llm = FakeJudge('{"verdict": "entailed", "reason": "ok"}')

    check_entailment("The sky is blue.", ["The sky appears blue.", "Water is wet."], llm)

    assert "The sky is blue." in llm.last_user
    assert "The sky appears blue." in llm.last_user
    assert "Water is wet." in llm.last_user


def test_check_entailment_raises_for_missing_fields():
    llm = FakeJudge('{"verdict": "entailed"}')

    with pytest.raises(ValueError):
        check_entailment("claim", ["source"], llm)


def test_check_entailment_raises_for_unexpected_verdict_value():
    llm = FakeJudge('{"verdict": "maybe", "reason": "unsure"}')

    with pytest.raises(ValueError):
        check_entailment("claim", ["source"], llm)
