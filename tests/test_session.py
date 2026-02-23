from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from scorer.db import session as session_module
from scorer.db.base import Base
from scorer.db.models import ScoringRun
from scorer.db.session import get_session


def test_get_session_yields_a_working_session(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    test_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(session_module, "SessionLocal", test_factory)

    gen = get_session()
    db = next(gen)
    db.add(
        ScoringRun(
            answer="Paris is the capital of France.",
            num_sources=1,
            score=1.0,
            num_flagged_claims=0,
        )
    )
    db.commit()
    assert db.query(ScoringRun).count() == 1

    gen.close()  # must not raise


def test_make_session_factory_builds_a_working_sessionmaker():
    factory = session_module.make_session_factory("sqlite:///:memory:")
    Base.metadata.create_all(factory().get_bind())

    with factory() as db:
        db.add(
            ScoringRun(
                answer="The Eiffel Tower is in Berlin.",
                num_sources=1,
                score=0.0,
                num_flagged_claims=1,
            )
        )
        db.commit()
        assert db.query(ScoringRun).count() == 1
