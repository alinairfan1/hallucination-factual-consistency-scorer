import anthropic
from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session

from scorer.config import settings
from scorer.db.models import ScoringRun
from scorer.db.session import get_session
from scorer.llm_client import AnthropicJudge
from scorer.schemas import ScoreRequest, ScoreResponse
from scorer.scoring import run_scoring

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
    result = run_scoring(request.answer, request.sources, llm)

    log = ScoringRun(
        answer=request.answer,
        num_sources=len(request.sources),
        score=result.score,
        num_flagged_claims=len(result.flagged_claims),
    )
    session.add(log)
    session.commit()

    return result
