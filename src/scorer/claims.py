from typing import Protocol

from scorer.llm_client import parse_json_response


class Judge(Protocol):
    def complete(self, system: str, user: str) -> str: ...


EXTRACTION_SYSTEM_PROMPT = (
    "You are a claim extraction system. Given a piece of text, break it into a list "
    "of atomic, self-contained, independently-checkable factual claims. Each claim "
    "must stand alone: resolve pronouns and implicit references so no claim depends "
    "on another claim's context. Respond with ONLY a JSON array of strings (the "
    "claims), no other text. If the text contains no checkable factual claims, "
    "respond with []."
)


def extract_claims(answer: str, llm: Judge) -> list[str]:
    response_text = llm.complete(system=EXTRACTION_SYSTEM_PROMPT, user=answer)
    claims = parse_json_response(response_text)

    if not isinstance(claims, list):
        raise ValueError(f"Expected a JSON array of claims, got: {response_text!r}")

    return [str(claim) for claim in claims]
