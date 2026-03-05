from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from scorer.benchmark.metrics import CalibrationBucket, ClassificationMetrics
from scorer.benchmark.persistence import save_benchmark_run
from scorer.benchmark.runner import QueryResult
from scorer.db.base import Base
from scorer.db.models import BenchmarkRun
from scorer.schemas import ClaimVerdict


def test_save_benchmark_run_persists_run_and_example_results():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    results = [
        QueryResult(
            index=0,
            actual_label="supported",
            predicted_label="supported",
            score=1.0,
            num_flagged_claims=0,
            answer='Question: "What is the capital of France?" Answer: Paris',
            sources=["Paris is the capital of France."],
            claims=[ClaimVerdict(claim="The capital of France is Paris.", verdict="entailed", reason="ok")],
        ),
        QueryResult(
            index=1,
            actual_label="hallucinated",
            predicted_label="hallucinated",
            score=0.0,
            num_flagged_claims=0,
            answer="a2",
            sources=["s2"],
            error="malformed judge JSON",
        ),
    ]
    metrics = ClassificationMetrics(precision=0.87, recall=0.80, f1=0.833, naive_baseline_f1=0.0)
    calibration = [CalibrationBucket(score=1.0, count=1, empirical_supported_rate=1.0)]

    with Session(engine) as session:
        run = save_benchmark_run(
            session,
            results,
            metrics,
            calibration,
            dataset_name="HaluEval QA (100-example subset)",
            judge_model="mistral-large-latest",
        )

        fetched = session.query(BenchmarkRun).one()
        assert fetched.id == run.id
        assert fetched.f1 == 83.3
        assert fetched.naive_length_heuristic_f1 == 73.7
        # The errored example is excluded — no real claim detail to show for it.
        assert len(fetched.examples) == 1
        assert fetched.examples[0].question == "What is the capital of France?"
        assert fetched.examples[0].answer == "Paris"
        assert fetched.examples[0].claims[0]["verdict"] == "entailed"
