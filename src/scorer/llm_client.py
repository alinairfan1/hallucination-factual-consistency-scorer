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


# initial_interval=500ms, max_interval=60s, exponent=1.5, max_elapsed_time=300s
DEFAULT_JUDGE_RETRY_CONFIG = RetryConfig(
    "backoff",
    BackoffStrategy(500, 60_000, 1.5, 300_000),
    True,
)

# httpx defaults to a 5s timeout, which a slow judge completion can exceed;
# without an explicit ceiling here, a merely-slow (not failed) call gets
# treated as a connection error and re-billed on every retry.
DEFAULT_JUDGE_TIMEOUT_MS = 120_000


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
        message = response.choices[0].message
        if message is None or message.content is None:
            raise ValueError(f"Expected a message with content, got: {message!r}")

        content = message.content
        if isinstance(content, str):
            return content

        text_parts = []
        for chunk in content:
            if not hasattr(chunk, "text"):
                raise ValueError(f"Expected a text content chunk, got: {chunk!r}")
            text_parts.append(chunk.text)
        return "".join(text_parts)
