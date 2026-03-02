from dataclasses import dataclass

import pytest
from mistralai.client.utils import RetryConfig

from scorer.llm_client import MistralJudge, parse_json_response


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


@dataclass
class FakeMistralMessage:
    content: str | None


@dataclass
class FakeMistralChoice:
    message: FakeMistralMessage


@dataclass
class FakeMistralResponse:
    choices: list[FakeMistralChoice]


class FakeMistralChat:
    def __init__(self, response: FakeMistralResponse) -> None:
        self._response = response
        self.last_kwargs: dict | None = None

    def complete(self, **kwargs):
        self.last_kwargs = kwargs
        return self._response


class FakeMistralClient:
    def __init__(self, response: FakeMistralResponse) -> None:
        self.chat = FakeMistralChat(response)


def test_mistral_judge_extracts_message_content():
    fake_response = FakeMistralResponse(
        choices=[FakeMistralChoice(message=FakeMistralMessage(content="hello"))]
    )
    client = FakeMistralClient(fake_response)
    judge = MistralJudge(model="mistral-large-latest", client=client)

    result = judge.complete(system="Be terse.", user="Say hi.")

    assert result == "hello"


def test_mistral_judge_passes_system_user_model_and_temperature():
    fake_response = FakeMistralResponse(
        choices=[FakeMistralChoice(message=FakeMistralMessage(content="hi"))]
    )
    client = FakeMistralClient(fake_response)
    judge = MistralJudge(model="mistral-large-latest", client=client)

    judge.complete(system="Be terse.", user="Say hi.")

    assert client.chat.last_kwargs["model"] == "mistral-large-latest"
    assert client.chat.last_kwargs["temperature"] == 0.0
    assert client.chat.last_kwargs["messages"] == [
        {"role": "system", "content": "Be terse."},
        {"role": "user", "content": "Say hi."},
    ]


def test_default_judge_retry_config_uses_bounded_exponential_backoff():
    from scorer.llm_client import DEFAULT_JUDGE_RETRY_CONFIG

    assert isinstance(DEFAULT_JUDGE_RETRY_CONFIG, RetryConfig)
    assert DEFAULT_JUDGE_RETRY_CONFIG.strategy == "backoff"
    assert DEFAULT_JUDGE_RETRY_CONFIG.backoff.initial_interval == 500
    assert DEFAULT_JUDGE_RETRY_CONFIG.backoff.max_interval == 60_000
    assert DEFAULT_JUDGE_RETRY_CONFIG.backoff.exponent == 1.5
    assert DEFAULT_JUDGE_RETRY_CONFIG.backoff.max_elapsed_time == 300_000
    assert DEFAULT_JUDGE_RETRY_CONFIG.retry_connection_errors is True


def test_mistral_judge_raises_for_missing_message_content():
    fake_response = FakeMistralResponse(
        choices=[FakeMistralChoice(message=FakeMistralMessage(content=None))]
    )
    client = FakeMistralClient(fake_response)
    judge = MistralJudge(model="mistral-large-latest", client=client)

    with pytest.raises(ValueError):
        judge.complete(system="Be terse.", user="Say hi.")
