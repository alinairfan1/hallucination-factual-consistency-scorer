import anthropic
from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session

from scorer.aggregation import aggregate
from scorer.claims import extract_claims
from scorer.config import settings
from scorer.db.models import ScoringRun
from scorer.db.session import get_session
from scorer.entailment import check_entailment
from scorer.llm_client import AnthropicJudge
from scorer.schemas import ScoreRequest, ScoreResponse

app = FastAPI(title="Hallucination / Factual-Consistency Scorer")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def get_llm_client() -> AnthropicJudge:
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return AnthropicJudge(model=settings.judge_model, client=client)


@app.post("/v1/score", response_model=ScoreResponse)
def score(
    request: ScoreRequest,
    session: Session = Depends(get_session),
    llm: AnthropicJudge = Depends(get_llm_client),
) -> ScoreResponse:
    claims = extract_claims(request.answer, llm)

    claim_verdicts = []
    for claim in claims:
        verdict, reason = check_entailment(claim, request.sources, llm)
        claim_verdicts.append((claim, verdict, reason))

    score_value, flagged_claims = aggregate(claim_verdicts)

    log = ScoringRun(
        answer=request.answer,
        num_sources=len(request.sources),
        score=score_value,
        num_flagged_claims=len(flagged_claims),
    )
    session.add(log)
    session.commit()

    return ScoreResponse(score=score_value, flagged_claims=flagged_claims)
