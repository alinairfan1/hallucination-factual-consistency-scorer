from scorer.benchmark.metrics import compute_calibration, compute_classification_metrics
from scorer.benchmark.runner import QueryResult


def test_compute_classification_metrics_perfect_predictions():
    results = [
        QueryResult(
            index=0, actual_label="supported", predicted_label="supported",
            score=1.0, num_flagged_claims=0,
        ),
        QueryResult(
            index=1, actual_label="hallucinated", predicted_label="hallucinated",
            score=0.0, num_flagged_claims=1,
        ),
    ]

    metrics = compute_classification_metrics(results)

    assert metrics.precision == 1.0
    assert metrics.recall == 1.0
    assert metrics.f1 == 1.0


def test_compute_classification_metrics_all_wrong_predictions():
    results = [
        QueryResult(
            index=0, actual_label="hallucinated", predicted_label="supported",
            score=1.0, num_flagged_claims=0,
        ),
    ]

    metrics = compute_classification_metrics(results)

    assert metrics.precision == 0.0
    assert metrics.recall == 0.0
    assert metrics.f1 == 0.0


def test_compute_classification_metrics_mixed_predictions():
    results = [
        QueryResult(
            index=0, actual_label="hallucinated", predicted_label="hallucinated",
            score=0.0, num_flagged_claims=1,
        ),
        QueryResult(
            index=1, actual_label="supported", predicted_label="hallucinated",
            score=0.0, num_flagged_claims=1,
        ),
        QueryResult(
            index=2, actual_label="hallucinated", predicted_label="supported",
            score=1.0, num_flagged_claims=0,
        ),
    ]

    metrics = compute_classification_metrics(results)

    assert metrics.precision == 0.5
    assert round(metrics.recall, 4) == 0.5
    assert round(metrics.f1, 4) == 0.5


def test_naive_baseline_f1_is_zero_when_hallucinated_examples_exist():
    results = [
        QueryResult(
            index=0, actual_label="hallucinated", predicted_label="hallucinated",
            score=0.0, num_flagged_claims=1,
        ),
        QueryResult(
            index=1, actual_label="supported", predicted_label="supported",
            score=1.0, num_flagged_claims=0,
        ),
    ]

    metrics = compute_classification_metrics(results)

    assert metrics.naive_baseline_f1 == 0.0


def test_naive_baseline_f1_is_one_when_no_hallucinated_examples():
    results = [
        QueryResult(
            index=0, actual_label="supported", predicted_label="supported",
            score=1.0, num_flagged_claims=0,
        ),
    ]

    metrics = compute_classification_metrics(results)

    assert metrics.naive_baseline_f1 == 1.0


def test_compute_calibration_groups_by_exact_score_value():
    results = [
        QueryResult(
            index=0, actual_label="supported", predicted_label="supported",
            score=1.0, num_flagged_claims=0,
        ),
        QueryResult(
            index=1, actual_label="supported", predicted_label="supported",
            score=1.0, num_flagged_claims=0,
        ),
        QueryResult(
            index=2, actual_label="hallucinated", predicted_label="hallucinated",
            score=0.0, num_flagged_claims=1,
        ),
    ]

    calibration = compute_calibration(results)

    by_score = {b.score: b for b in calibration}
    assert by_score[1.0].count == 2
    assert by_score[1.0].empirical_supported_rate == 1.0
    assert by_score[0.0].count == 1
    assert by_score[0.0].empirical_supported_rate == 0.0
