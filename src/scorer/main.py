from functools import lru_cache
from typing import Literal, cast

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from mistralai.client import Mistral
from sqlalchemy import desc
from sqlalchemy.orm import Session

from scorer.config import settings
from scorer.db.models import BenchmarkRun, ScoringRun
from scorer.db.session import get_session
from scorer.llm_client import DEFAULT_JUDGE_RETRY_CONFIG, DEFAULT_JUDGE_TIMEOUT_MS, MistralJudge
from scorer.schemas import (
    BenchmarkExampleResponse,
    BenchmarkSummaryResponse,
    CalibrationBucketResponse,
    ClaimVerdict,
    LiveScoringRunResponse,
    ScoreRequest,
    ScoreResponse,
)
from scorer.scoring import run_scoring

app = FastAPI(title="Hallucination / Factual-Consistency Scorer")

# The report viewer (web/) is a separately-hosted static SPA with no cookies or
# auth on this API — every route here is either a read-only GET or a scoring
# POST with no session state, so permissive CORS carries no CSRF/credential
# risk and avoids hardcoding the dev server's port.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@lru_cache
def get_llm_client() -> MistralJudge:
    client = Mistral(
        api_key=settings.mistral_api_key,
        retry_config=DEFAULT_JUDGE_RETRY_CONFIG,
        timeout_ms=DEFAULT_JUDGE_TIMEOUT_MS,
    )
    return MistralJudge(model=settings.judge_model, client=client)


@app.post("/v1/score", response_model=ScoreResponse)
def score(
    request: ScoreRequest,
    session: Session = Depends(get_session),
    llm: MistralJudge = Depends(get_llm_client),
) -> ScoreResponse:
    result = run_scoring(request.answer, request.sources, llm)

    log = ScoringRun(
        answer=request.answer,
        num_sources=len(request.sources),
        score=result.score,
        num_flagged_claims=len(result.flagged_claims),
        sources=request.sources,
        claims=[claim.model_dump() for claim in result.claims],
    )
    session.add(log)
    session.commit()

    return result


@app.get("/v1/benchmark", response_model=BenchmarkSummaryResponse)
def get_latest_benchmark_run(session: Session = Depends(get_session)) -> BenchmarkSummaryResponse:
    run = session.query(BenchmarkRun).order_by(desc(BenchmarkRun.created_at)).first()
    if run is None:
        raise HTTPException(
            status_code=404,
            detail="No benchmark run has been persisted yet — run `scorer-benchmark`.",
        )

    return BenchmarkSummaryResponse(
        precision=run.precision,
        recall=run.recall,
        f1=run.f1,
        naiveAlwaysSupportedF1=run.naive_always_supported_f1,
        naiveLengthHeuristicF1=run.naive_length_heuristic_f1,
        exampleCount=run.example_count,
        judgeModel=run.judge_model,
        datasetName=run.dataset_name,
        calibration=[CalibrationBucketResponse.model_validate(bucket) for bucket in run.calibration],
        examples=[
            BenchmarkExampleResponse(
                id=example.id,
                question=example.question,
                answer=example.answer,
                sources=example.sources,
                humanLabel=cast(Literal["supported", "hallucinated"], example.human_label),
                score=example.score,
                claims=[ClaimVerdict.model_validate(claim) for claim in example.claims],
            )
            for example in run.examples
        ],
    )


@app.get("/v1/scoring-runs", response_model=list[LiveScoringRunResponse])
def list_scoring_runs(
    limit: int = 50, session: Session = Depends(get_session)
) -> list[LiveScoringRunResponse]:
    runs = (
        session.query(ScoringRun).order_by(desc(ScoringRun.created_at)).limit(limit).all()
    )
    return [
        LiveScoringRunResponse(
            id=run.id,
            timestamp=run.created_at,
            answer=run.answer,
            sources=run.sources or [],
            score=run.score,
            claims=[ClaimVerdict.model_validate(claim) for claim in (run.claims or [])],
        )
        for run in runs
    ]
