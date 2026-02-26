import argparse
from pathlib import Path

import anthropic

from scorer.benchmark.metrics import compute_calibration, compute_classification_metrics
from scorer.benchmark.report import format_report
from scorer.benchmark.runner import run_benchmark
from scorer.config import settings
from scorer.dataset import load_examples
from scorer.llm_client import AnthropicJudge

DEFAULT_DATASET_PATH = Path("data/halueval_qa_benchmark.jsonl")


def build_judge() -> AnthropicJudge:
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return AnthropicJudge(model=settings.judge_model, client=client)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark the scorer against a hallucination-labeled dataset."
    )
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument("--threshold", type=float, default=1.0)
    args = parser.parse_args()

    examples = load_examples(args.dataset)
    judge = build_judge()
    results = run_benchmark(examples, judge, args.threshold)

    metrics = compute_classification_metrics(results)
    calibration = compute_calibration(results)
    print(format_report(metrics, calibration, len(examples)))


if __name__ == "__main__":
    main()
