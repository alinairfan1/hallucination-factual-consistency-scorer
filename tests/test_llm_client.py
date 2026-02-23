from dataclasses import dataclass

import pytest

from scorer.llm_client import AnthropicJudge, parse_json_response


@dataclass
class FakeContentBlock:
    type: str
    text: str


@dataclass
class FakeResponse:
    content: list[FakeContentBlock]


class FakeAnthropicMessages:
    def __init__(self, response: FakeResponse) -> None:
        self._response = response
        self.last_kwargs: dict | None = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        return self._response


class FakeAnthropicClient:
    def __init__(self, response: FakeResponse) -> None:
        self.messages = FakeAnthropicMessages(response)


def test_complete_extracts_text_content():
    fake_response = FakeResponse(content=[FakeContentBlock(type="text", text="hello")])
    client = FakeAnthropicClient(fake_response)
    judge = AnthropicJudge(model="claude-sonnet-5", client=client)

    result = judge.complete(system="Be terse.", user="Say hi.")

    assert result == "hello"


def test_complete_concatenates_multiple_text_blocks():
    fake_response = FakeResponse(
        content=[
            FakeContentBlock(type="text", text="hel"),
            FakeContentBlock(type="text", text="lo"),
        ]
    )
    client = FakeAnthropicClient(fake_response)
    judge = AnthropicJudge(model="claude-sonnet-5", client=client)

    assert judge.complete(system="sys", user="usr") == "hello"


def test_complete_passes_system_user_and_model_correctly():
    fake_response = FakeResponse(content=[FakeContentBlock(type="text", text="hi")])
    client = FakeAnthropicClient(fake_response)
    judge = AnthropicJudge(model="claude-sonnet-5", client=client)

    judge.complete(system="Be terse.", user="Say hi.")

    assert client.messages.last_kwargs["system"] == "Be terse."
    assert client.messages.last_kwargs["messages"] == [{"role": "user", "content": "Say hi."}]
    assert client.messages.last_kwargs["model"] == "claude-sonnet-5"


def test_parse_json_response_parses_plain_json():
    assert parse_json_response('{"a": 1}') == {"a": 1}


def test_parse_json_response_strips_markdown_fence_with_json_tag():
    assert parse_json_response('```json\n{"a": 1}\n```') == {"a": 1}


def test_parse_json_response_strips_plain_markdown_fence():
    assert parse_json_response('```\n["one", "two"]\n```') == ["one", "two"]


def test_parse_json_response_raises_clear_error_for_invalid_json():
    with pytest.raises(ValueError) as exc_info:
        parse_json_response("not json")
    assert "not json" in str(exc_info.value)
