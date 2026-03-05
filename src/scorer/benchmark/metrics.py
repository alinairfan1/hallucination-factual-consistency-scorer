from dataclasses import dataclass

from scorer.benchmark.runner import QueryResult

# Best achievable F1 from a single answer-length threshold classifier over
# data/halueval_qa_benchmark.jsonl, documented in data/README.md. This is a
# property of the dataset text, not something a single benchmark run
# computes, so it's a fixed constant rather than derived from `results`.
NAIVE_LENGTH_HEURISTIC_F1 = 73.7


@dataclass
class ClassificationMetrics:
    precision: float
    recall: float
    f1: float
    naive_baseline_f1: float
    error_count: int = 0


def compute_classification_metrics(results: list[QueryResult]) -> ClassificationMetrics:
    # Examples where run_benchmark caught a ValueError (malformed judge JSON)
    # carry a fail-safe predicted_label that isn't a real classification
    # decision. Excluding them here keeps precision/recall/F1 from being
    # silently skewed by judge-response failures; error_count still surfaces
    # how many were dropped so it isn't swept under the rug.
    scored_results = [r for r in results if r.error is None]
    error_count = len(results) - len(scored_results)

    tp = sum(
        1
        for r in scored_results
        if r.predicted_label == "hallucinated" and r.actual_label == "hallucinated"
    )
    fp = sum(
        1
        for r in scored_results
        if r.predicted_label == "hallucinated" and r.actual_label == "supported"
    )
    fn = sum(
        1
        for r in scored_results
        if r.predicted_label == "supported" and r.actual_label == "hallucinated"
    )

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    # Naive baseline: always predict "supported". Its recall is 0 whenever at
    # least one example is actually "hallucinated" (per PLANNING.md §7's "F1
    # clearly above a naive baseline like 'always say supported'"), giving an
    # F1 of 0.0 in that case; 1.0 only in the degenerate all-supported case.
    has_hallucinated = any(r.actual_label == "hallucinated" for r in scored_results)
    naive_baseline_f1 = 0.0 if has_hallucinated else 1.0

    return ClassificationMetrics(
        precision=precision,
        recall=recall,
        f1=f1,
        naive_baseline_f1=naive_baseline_f1,
        error_count=error_count,
    )


@dataclass
class CalibrationBucket:
    score: float
    count: int
    empirical_supported_rate: float


def compute_calibration(results: list[QueryResult]) -> list[CalibrationBucket]:
    buckets: dict[float, list[QueryResult]] = {}
    for r in results:
        if r.error is not None:
            # Fail-safe score=0.0 from a caught ValueError isn't a real
            # calibration point; including it would misrepresent what
            # score=0.0 means empirically.
            continue
        buckets.setdefault(r.score, []).append(r)

    calibration = []
    for score in sorted(buckets):
        group = buckets[score]
        supported_count = sum(1 for r in group if r.actual_label == "supported")
        calibration.append(
            CalibrationBucket(
                score=score,
                count=len(group),
                empirical_supported_rate=supported_count / len(group),
            )
        )
    return calibration
