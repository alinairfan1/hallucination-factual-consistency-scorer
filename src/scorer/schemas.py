from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ScoreRequest(BaseModel):
    answer: str
    sources: list[str]


class FlaggedClaim(BaseModel):
    claim: str
    verdict: Literal["contradicted", "not_enough_info"]
    reason: str


class ClaimVerdict(BaseModel):
    claim: str
    verdict: Literal["entailed", "contradicted", "not_enough_info"]
    reason: str


class ScoreResponse(BaseModel):
    score: float
    flagged_claims: list[FlaggedClaim]
    claims: list[ClaimVerdict]


# --- Report-viewer read API (GET /v1/benchmark, GET /v1/scoring-runs) ---
# Field names are camelCase to match the report viewer's TypeScript types
# (web/src/types.ts) directly, since this API exists specifically to feed it.


class CalibrationBucketResponse(BaseModel):
    score: float
    count: int
    empiricalSupportedRate: float


class BenchmarkExampleResponse(BaseModel):
    id: str
    question: str
    answer: str
    sources: list[str]
    humanLabel: Literal["supported", "hallucinated"]
    score: float
    claims: list[ClaimVerdict]


class BenchmarkSummaryResponse(BaseModel):
    precision: float
    recall: float
    f1: float
    naiveAlwaysSupportedF1: float
    naiveLengthHeuristicF1: float
    exampleCount: int
    judgeModel: str
    datasetName: str
    calibration: list[CalibrationBucketResponse]
    examples: list[BenchmarkExampleResponse]


class LiveScoringRunResponse(BaseModel):
    id: str
    timestamp: datetime
    answer: str
    sources: list[str]
    score: float
    claims: list[ClaimVerdict]
