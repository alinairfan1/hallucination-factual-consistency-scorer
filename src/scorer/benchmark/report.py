from scorer.benchmark.metrics import CalibrationBucket, ClassificationMetrics


def format_report(
    metrics: ClassificationMetrics, calibration: list[CalibrationBucket], num_examples: int
) -> str:
    lines = [
        f"Hallucination Scorer Benchmark — {num_examples} examples",
        "-" * 50,
        f"Precision: {metrics.precision:.1%}",
        f"Recall:    {metrics.recall:.1%}",
        f"F1:        {metrics.f1:.1%}  "
        f"(naive 'always supported' baseline: {metrics.naive_baseline_f1:.1%})",
    ]
    if metrics.error_count:
        lines.append(
            f"Errors:    {metrics.error_count} example(s) failed with malformed judge "
            "output and were excluded from precision/recall/F1 above"
        )
    lines += [
        "",
        "Calibration (score -> empirical supported rate):",
    ]
    for bucket in calibration:
        lines.append(
            f"  score={bucket.score:.2f}  n={bucket.count:<4}  "
            f"empirical_supported_rate={bucket.empirical_supported_rate:.1%}"
        )
    return "\n".join(lines)
