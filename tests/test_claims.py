import pytest

from scorer.claims import extract_claims


class FakeJudge:
    def __init__(self, response_text: str) -> None:
        self.response_text = response_text
        self.last_system: str | None = None
        self.last_user: str | None = None

    def complete(self, system: str, user: str) -> str:
        self.last_system = system
        self.last_user = user
        return self.response_text


def test_extract_claims_parses_json_array():
    llm = FakeJudge('["Paris is the capital of France.", "The tower is 330m tall."]')

    claims = extract_claims(
        "Paris is the capital of France and the tower is 330m tall.", llm
    )

    assert claims == ["Paris is the capital of France.", "The tower is 330m tall."]


def test_extract_claims_passes_answer_as_user_message():
    llm = FakeJudge("[]")

    extract_claims("some answer", llm)

    assert llm.last_user == "some answer"


def test_extract_claims_returns_empty_list_for_no_claims():
    llm = FakeJudge("[]")

    assert extract_claims("Hello!", llm) == []


def test_extract_claims_raises_for_non_list_response():
    llm = FakeJudge('{"not": "a list"}')

    with pytest.raises(ValueError):
        extract_claims("some answer", llm)
