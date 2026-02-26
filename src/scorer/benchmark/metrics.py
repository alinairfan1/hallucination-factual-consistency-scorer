from dataclasses import dataclass

from scorer.benchmark.runner import QueryResult


@dataclass
class ClassificationMetrics:
    precision: float
    recall: float
    f1: float
    naive_baseline_f1: float


def compute_classification_metrics(results: list[QueryResult]) -> ClassificationMetrics:
    tp = sum(
        1 for r in results if r.predicted_label == "hallucinated" and r.actual_label == "hallucinated"
    )
    fp = sum(
        1 for r in results if r.predicted_label == "hallucinated" and r.actual_label == "supported"
    )
    fn = sum(
        1 for r in results if r.predicted_label == "supported" and r.actual_label == "hallucinated"
    )

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    # Naive baseline: always predict "supported". Its recall is 0 whenever at
    # least one example is actually "hallucinated" (per PLANNING.md §7's "F1
    # clearly above a naive baseline like 'always say supported'"), giving an
    # F1 of 0.0 in that case; 1.0 only in the degenerate all-supported case.
    has_hallucinated = any(r.actual_label == "hallucinated" for r in results)
    naive_baseline_f1 = 0.0 if has_hallucinated else 1.0

    return ClassificationMetrics(
        precision=precision, recall=recall, f1=f1, naive_baseline_f1=naive_baseline_f1
    )


@dataclass
class CalibrationBucket:
    score: float
    count: int
    empirical_supported_rate: float


def compute_calibration(results: list[QueryResult]) -> list[CalibrationBucket]:
    buckets: dict[float, list[QueryResult]] = {}
    for r in results:
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
