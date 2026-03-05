from sqlalchemy.orm import Session

from scorer.benchmark.metrics import (
    NAIVE_LENGTH_HEURISTIC_F1,
    CalibrationBucket,
    ClassificationMetrics,
)
from scorer.benchmark.qa_split import split_question_answer
from scorer.benchmark.runner import QueryResult
from scorer.db.models import BenchmarkExampleResult, BenchmarkRun


def save_benchmark_run(
    session: Session,
    results: list[QueryResult],
    metrics: ClassificationMetrics,
    calibration: list[CalibrationBucket],
    dataset_name: str,
    judge_model: str,
) -> BenchmarkRun:
    """Persist a completed benchmark run so the report viewer can display it.

    Errored examples (a malformed judge response or an API-boundary failure —
    see run_benchmark's own handling) are skipped: there's no real claim
    detail to show for them, and they're already excluded from `metrics`.
    """
    run = BenchmarkRun(
        dataset_name=dataset_name,
        judge_model=judge_model,
        example_count=len(results),
        precision=metrics.precision * 100,
        recall=metrics.recall * 100,
        f1=metrics.f1 * 100,
        naive_always_supported_f1=metrics.naive_baseline_f1 * 100,
        naive_length_heuristic_f1=NAIVE_LENGTH_HEURISTIC_F1,
        calibration=[
            {
                "score": bucket.score,
                "count": bucket.count,
                "empiricalSupportedRate": bucket.empirical_supported_rate * 100,
            }
            for bucket in calibration
        ],
    )
    session.add(run)
    session.flush()

    for result in results:
        if result.error is not None:
            continue
        question, answer = split_question_answer(result.answer)
        session.add(
            BenchmarkExampleResult(
                benchmark_run_id=run.id,
                example_index=result.index,
                question=question,
                answer=answer,
                sources=result.sources,
                human_label=result.actual_label,
                score=result.score,
                claims=[claim.model_dump() for claim in result.claims],
            )
        )

    session.commit()
    return run
