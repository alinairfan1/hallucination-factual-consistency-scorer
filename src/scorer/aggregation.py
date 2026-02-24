from scorer.entailment import Verdict
from scorer.schemas import FlaggedClaim


def aggregate(claim_verdicts: list[tuple[str, Verdict, str]]) -> tuple[float, list[FlaggedClaim]]:
    if not claim_verdicts:
        return 1.0, []

    entailed_count = sum(1 for _, verdict, _ in claim_verdicts if verdict == "entailed")
    score = entailed_count / len(claim_verdicts)

    flagged_claims: list[FlaggedClaim] = []
    for claim, verdict, reason in claim_verdicts:
        if verdict == "entailed":
            continue
        flagged_claims.append(FlaggedClaim(claim=claim, verdict=verdict, reason=reason))

    return score, flagged_claims
