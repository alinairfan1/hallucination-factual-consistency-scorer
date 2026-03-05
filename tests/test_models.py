from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from scorer.db.base import Base
from scorer.db.models import BenchmarkExampleResult, BenchmarkRun, ScoringRun


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


def test_scoring_run_stores_sources_and_claims_json():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        run = ScoringRun(
            answer="Paris is the capital of France.",
            num_sources=1,
            score=1.0,
            num_flagged_claims=0,
            sources=["Paris is the capital of France."],
            claims=[{"claim": "Paris is the capital of France.", "verdict": "entailed", "reason": "ok"}],
        )
        session.add(run)
        session.commit()

        fetched = session.query(ScoringRun).one()
        assert fetched.sources == ["Paris is the capital of France."]
        assert fetched.claims[0]["verdict"] == "entailed"


def test_benchmark_run_round_trip_with_example_results():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        run = BenchmarkRun(
            dataset_name="HaluEval QA (100-example subset)",
            judge_model="mistral-large-latest",
            example_count=1,
            precision=87.0,
            recall=80.0,
            f1=83.3,
            naive_always_supported_f1=0.0,
            naive_length_heuristic_f1=73.7,
            calibration=[{"score": 1.0, "count": 54, "empiricalSupportedRate": 81.5}],
        )
        session.add(run)
        session.flush()

        example = BenchmarkExampleResult(
            benchmark_run_id=run.id,
            example_index=0,
            question="What is the capital of France?",
            answer="Paris",
            sources=["Paris is the capital of France."],
            human_label="supported",
            score=1.0,
            claims=[{"claim": "The capital of France is Paris.", "verdict": "entailed", "reason": "ok"}],
        )
        session.add(example)
        session.commit()

        fetched_run = session.query(BenchmarkRun).one()
        assert fetched_run.f1 == 83.3
        assert len(fetched_run.examples) == 1
        assert fetched_run.examples[0].question == "What is the capital of France?"
        assert fetched_run.examples[0].claims[0]["verdict"] == "entailed"
