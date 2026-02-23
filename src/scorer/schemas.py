from typing import Literal

from pydantic import BaseModel


class ScoreRequest(BaseModel):
    answer: str
    sources: list[str]


class FlaggedClaim(BaseModel):
    claim: str
    verdict: Literal["contradicted", "not_enough_info"]
    reason: str


class ScoreResponse(BaseModel):
    score: float
    flagged_claims: list[FlaggedClaim]
