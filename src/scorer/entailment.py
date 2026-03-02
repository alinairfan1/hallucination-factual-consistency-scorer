from typing import Literal, Protocol

from scorer.llm_client import parse_json_response

Verdict = Literal["entailed", "contradicted", "not_enough_info"]

_VALID_VERDICTS = {"entailed", "contradicted", "not_enough_info"}


class Judge(Protocol):
    def complete(self, system: str, user: str) -> str: ...


ENTAILMENT_SYSTEM_PROMPT = (
    "You are a rigorous fact-checking judge. Given a CLAIM and a set of SOURCE "
    "documents, decide whether the claim is entailed, contradicted, or "
    "not_enough_info with respect to the sources.\n\n"
    "Definitions:\n"
    "- entailed: the sources support the claim. This does not require identical "
    "wording — if the sources state or straightforwardly imply the claim through "
    'simple logical composition (e.g. "X has stores throughout Hawaii" entails "X\'s '
    'stores are located in Hawaii"), mark it entailed. Do not invent a secondary '
    "distinction the claim never asserted (e.g. don't read \"was based at X\" as "
    'claiming X is still active today just because a source calls X a "former" '
    "site; don't treat a person's age at the time in question as a claim about "
    "their age now).\n"
    "- contradicted: the sources state something inconsistent with the claim — "
    "this includes near-misses, where a specific number, date, or named "
    'entity/event in the claim differs from what the sources say (e.g. claim says '
    '"330 meters", sources say "324 meters"; claim says "the Korean War", sources '
    'describe World War II — a different, specific named event, not a paraphrase '
    "of it). For a comparative claim (which came first, who has more, who is "
    "older), first extract the specific dates/counts/quantities each side is being "
    "compared on, then explicitly compare them before deciding — do not judge a "
    "comparison from surface phrasing alone.\n"
    "- not_enough_info: the sources simply do not address the claim at all, so "
    "there is nothing to confirm or deny.\n\n"
    "Judge only what the sources actually say — do not use outside/world knowledge "
    "to fill gaps. Reserve contradicted/not_enough_info for a real inconsistency or "
    "a real informational gap, not for an alternate reading you had to construct.\n\n"
    "Work out your reasoning first, then state your verdict — never decide the "
    "verdict before writing the reason, since your reason is what the verdict must "
    "follow from, not a justification written after the fact. Respond with ONLY a "
    "JSON object with 'reason' before 'verdict', of the form: "
    '{"reason": "<one sentence of reasoning, including any numbers/dates/quantities '
    'you compared>", "verdict": "entailed" | "contradicted" | "not_enough_info"}.'
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
