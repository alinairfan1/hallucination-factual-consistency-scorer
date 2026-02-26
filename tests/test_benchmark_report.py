from scorer.benchmark.metrics import CalibrationBucket, ClassificationMetrics
from scorer.benchmark.report import format_report


def test_format_report_includes_metrics_and_calibration():
    metrics = ClassificationMetrics(precision=0.8, recall=0.75, f1=0.774, naive_baseline_f1=0.0)
    calibration = [
        CalibrationBucket(score=1.0, count=10, empirical_supported_rate=0.9),
        CalibrationBucket(score=0.0, count=8, empirical_supported_rate=0.1),
    ]

    report = format_report(metrics, calibration, num_examples=18)

    assert "18 examples" in report
    assert "80.0%" in report
    assert "75.0%" in report
    assert "score=1.00" in report
    assert "score=0.00" in report


def test_format_report_handles_empty_calibration():
    metrics = ClassificationMetrics(precision=0.0, recall=0.0, f1=0.0, naive_baseline_f1=1.0)

    report = format_report(metrics, [], num_examples=0)

    assert "0 examples" in report
