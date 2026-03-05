from typing import Protocol

from scorer.aggregation import aggregate
from scorer.claims import extract_claims
from scorer.entailment import check_entailment
from scorer.schemas import ClaimVerdict, ScoreResponse


class Judge(Protocol):
    def complete(self, system: str, user: str) -> str: ...


def run_scoring(answer: str, sources: list[str], llm: Judge) -> ScoreResponse:
    claims = extract_claims(answer, llm)

    claim_verdicts = []
    for claim in claims:
        verdict, reason = check_entailment(claim, sources, llm)
        claim_verdicts.append((claim, verdict, reason))

    score_value, flagged_claims = aggregate(claim_verdicts)
    all_claims = [
        ClaimVerdict(claim=claim, verdict=verdict, reason=reason)
        for claim, verdict, reason in claim_verdicts
    ]
    return ScoreResponse(score=score_value, flagged_claims=flagged_claims, claims=all_claims)
