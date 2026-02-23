import pytest
from pydantic import ValidationError

from scorer.schemas import FlaggedClaim, ScoreRequest, ScoreResponse


def test_score_request_accepts_answer_and_sources():
    req = ScoreRequest(answer="Paris is the capital of France.", sources=["Paris is France's capital."])
    assert req.answer == "Paris is the capital of France."
    assert req.sources == ["Paris is France's capital."]


def test_flagged_claim_accepts_valid_verdict():
    claim = FlaggedClaim(claim="The tower is 500m tall.", verdict="contradicted", reason="Sources say 330m.")
    assert claim.verdict == "contradicted"


def test_flagged_claim_rejects_invalid_verdict():
    with pytest.raises(ValidationError):
        FlaggedClaim(claim="The tower is 500m tall.", verdict="entailed", reason="n/a")


def test_score_response_round_trip():
    resp = ScoreResponse(
        score=0.75,
        flagged_claims=[
            FlaggedClaim(claim="The tower is 500m tall.", verdict="contradicted", reason="Sources say 330m."),
        ],
    )
    dumped = resp.model_dump()
    assert dumped["score"] == 0.75
    assert dumped["flagged_claims"][0]["verdict"] == "contradicted"
    restored = ScoreResponse.model_validate(dumped)
    assert restored == resp
