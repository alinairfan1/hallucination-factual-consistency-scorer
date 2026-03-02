import json
from typing import Any

from mistralai.client.utils import BackoffStrategy, RetryConfig


def parse_json_response(text: str) -> Any:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`").strip()
        if stripped.startswith("json"):
            stripped = stripped[len("json") :].strip()

    try:
        return json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Expected valid JSON from the LLM, got: {text!r}") from exc


DEFAULT_JUDGE_RETRY_CONFIG = RetryConfig(
    "backoff",
    BackoffStrategy(500, 60_000, 1.5, 300_000),
    True,
)


class MistralJudge:
    def __init__(self, model: str, client: Any) -> None:
        self.model = model
        self.client = client

    def complete(self, system: str, user: str) -> str:
        response = self.client.chat.complete(
            model=self.model,
            temperature=0.0,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.choices[0].message.content
