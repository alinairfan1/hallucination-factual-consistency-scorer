import re

# Matches the `Question: "<question>" Answer: <answer>` scaffolding every example in
# data/halueval_qa_benchmark.jsonl uses (see data/README.md) — not a general-purpose parser.
_QA_PATTERN = re.compile(r'^Question:\s*"(?P<question>.*)"\s*Answer:\s*(?P<answer>.*)$', re.DOTALL)


def split_question_answer(raw: str) -> tuple[str, str]:
    """Split a `Question: "..." Answer: ...` string into (question, answer).

    Returns ("", raw) unchanged when the text doesn't match that scaffolding —
    e.g. a live /v1/score call's free-text answer, which never has it.
    """
    match = _QA_PATTERN.match(raw.strip())
    if not match:
        return "", raw
    return match.group("question").strip(), match.group("answer").strip()
