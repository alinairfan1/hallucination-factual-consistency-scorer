from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from scorer.db.base import Base
from scorer.db.models import ScoringRun


def test_scoring_run_round_trip_in_sqlite():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        run = ScoringRun(
            answer="Paris is the capital of France.",
            num_sources=2,
            score=0.9,
            num_flagged_claims=0,
        )
        session.add(run)
        session.commit()

        fetched = session.query(ScoringRun).one()
        assert fetched.id is not None
        assert fetched.answer == "Paris is the capital of France."
        assert fetched.num_sources == 2
        assert fetched.score == 0.9
        assert fetched.num_flagged_claims == 0
        assert fetched.created_at is not None
