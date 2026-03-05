import argparse
from pathlib import Path

from mistralai.client import Mistral
from sqlalchemy.orm import sessionmaker

from scorer.benchmark.metrics import compute_calibration, compute_classification_metrics
from scorer.benchmark.persistence import save_benchmark_run
from scorer.benchmark.report import format_report
from scorer.benchmark.runner import run_benchmark
from scorer.config import settings
from scorer.dataset import load_examples
from scorer.db.session import make_session_factory
from scorer.llm_client import DEFAULT_JUDGE_RETRY_CONFIG, DEFAULT_JUDGE_TIMEOUT_MS, MistralJudge

DEFAULT_DATASET_PATH = Path("data/halueval_qa_benchmark.jsonl")


def build_judge() -> MistralJudge:
    client = Mistral(
        api_key=settings.mistral_api_key,
        retry_config=DEFAULT_JUDGE_RETRY_CONFIG,
        timeout_ms=DEFAULT_JUDGE_TIMEOUT_MS,
    )
    return MistralJudge(model=settings.judge_model, client=client)


def build_session_factory() -> sessionmaker:
    return make_session_factory(settings.database_url)


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

    session_factory = build_session_factory()
    with session_factory() as session:
        save_benchmark_run(
            session,
            results,
            metrics,
            calibration,
            dataset_name=args.dataset.name,
            judge_model=settings.judge_model,
        )


if __name__ == "__main__":
    main()
