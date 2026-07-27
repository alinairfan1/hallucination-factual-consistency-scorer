from typing import Protocol

from scorer.llm_client import parse_json_response


class Judge(Protocol):
    def complete(self, system: str, user: str) -> str: ...


EXTRACTION_SYSTEM_PROMPT = (
    "You are a claim extraction system for a fact-checking pipeline. Given a piece "
    "of text, break it into a list of atomic, self-contained, independently-checkable "
    "factual claims.\n\n"
    "Rules:\n"
    "- Each claim must stand alone: resolve pronouns and implicit references so no "
    "claim depends on another claim's context.\n"
    "- Each claim must express exactly one fact. Split compound statements (e.g. "
    '"X and Y") into separate claims for X and for Y.\n'
    "- Preserve exact numbers, dates, units, and proper nouns verbatim — do not "
    'round, paraphrase, or drop precision (e.g. keep "330 meters", not "tall").\n'
    "- Do not extract subjective opinions, greetings, or statements with no factual "
    'content (e.g. "Hello!", "That\'s a great question.").\n'
    '- If the text is a "Question: ... Answer: ..." pair, reconstruct the single '
    "factual claim the answer is asserting by combining the question and answer "
    "into a standalone declarative sentence — never extract [] just because the "
    "answer alone (e.g. a bare name or number) doesn't read as a complete sentence "
    "in isolation. Extract only what the ANSWER specifies: if the question's own "
    "phrasing includes extra descriptive detail about an entity (e.g. \"Dua Lipa, "
    'an English singer, songwriter and model, ... released in what year?"), do not '
    "extract those descriptive details as their own claims — they are the "
    "question's framing, not something the answer is asserting.\n"
    "- Never add information beyond what the text literally states, even if you "
    "recognize the subject and know more about it. If the answer names only some "
    "members of a group or gives a partial/truncated list, extract a claim about "
    "only the members actually named — do not complete the list from your own "
    "knowledge.\n"
    "- If the text contains no checkable factual claims, respond with [].\n\n"
    "Examples:\n"
    'Text: "The Eiffel Tower, built in 1889, is 330 meters tall and located in '
    'Paris."\n'
    'Claims: ["The Eiffel Tower was built in 1889.", "The Eiffel Tower is 330 '
    'meters tall.", "The Eiffel Tower is located in Paris."]\n\n'
    'Text: "Question: \\"What is the capital of France?\\" Answer: Berlin"\n'
    'Claims: ["The capital of France is Berlin."]\n\n'
    'Text: "Question: \\"Dua Lipa, an English singer and songwriter, released her '
    'debut album in what year?\\" Answer: 2017"\n'
    'Claims: ["Dua Lipa released her debut album in 2017."]\n\n'
    "Respond with ONLY a JSON array of strings (the claims), no other text."
)


def extract_claims(answer: str, llm: Judge) -> list[str]:
    response_text = llm.complete(system=EXTRACTION_SYSTEM_PROMPT, user=answer)
    claims = parse_json_response(response_text)

    if not isinstance(claims, list):
        raise TypeError(f"Expected a JSON array of claims, got: {response_text!r}")

    return [str(claim) for claim in claims]
