from typing import Literal, Protocol

from scorer.llm_client import parse_json_response

Verdict = Literal["entailed", "contradicted", "not_enough_info"]

_VALID_VERDICTS = {"entailed", "contradicted", "not_enough_info"}


class Judge(Protocol):
    def complete(self, system: str, user: str) -> str: ...


ENTAILMENT_SYSTEM_PROMPT = (
    "You are a fact-checking judge. Given a CLAIM and a set of SOURCE documents, "
    "decide whether the claim is entailed (fully supported by the sources), "
    "contradicted (the sources say something inconsistent with it), or "
    "not_enough_info (the sources don't say enough to decide either way). Respond "
    "with ONLY a JSON object of the form: "
    '{"verdict": "entailed" | "contradicted" | "not_enough_info", '
    '"reason": "<one sentence explanation>"}.'
)


def check_entailment(claim: str, sources: list[str], llm: Judge) -> tuple[Verdict, str]:
    sources_block = "\n".join(f"- {source}" for source in sources)
    user_prompt = f"CLAIM: {claim}\n\nSOURCES:\n{sources_block}"

    response_text = llm.complete(system=ENTAILMENT_SYSTEM_PROMPT, user=user_prompt)
    parsed = parse_json_response(response_text)

    if not isinstance(parsed, dict) or "verdict" not in parsed or "reason" not in parsed:
        raise ValueError(
            f"Expected a JSON object with 'verdict' and 'reason', got: {response_text!r}"
        )

    verdict = parsed["verdict"]
    if verdict not in _VALID_VERDICTS:
        raise ValueError(f"Unexpected verdict {verdict!r}, expected one of {_VALID_VERDICTS}")

    return verdict, str(parsed["reason"])
