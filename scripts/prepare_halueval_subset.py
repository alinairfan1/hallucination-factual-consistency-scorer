"""Fetch a subset of the HaluEval QA dataset and convert it into scorer.dataset's
JSONL shape.

Source: https://github.com/RUCAIBox/HaluEval (MIT License, RUCAIBox).
Each HaluEval QA row has {knowledge, question, right_answer, hallucinated_answer}.
This converts each row into two scorer.dataset.DatasetExample-shaped JSON lines:
one labeled "supported" (right_answer) and one labeled "hallucinated"
(hallucinated_answer), both grounded against the same knowledge as their source.
"""

import argparse
import json
import urllib.request
from pathlib import Path

HALUEVAL_QA_URL = "https://raw.githubusercontent.com/RUCAIBox/HaluEval/main/data/qa_data.json"


def convert_halueval_rows(raw_rows: list[dict], limit: int) -> list[dict]:
    examples = []
    for row in raw_rows[:limit]:
        sources = [row["knowledge"]]
        examples.append(
            {"answer": row["right_answer"], "sources": sources, "label": "supported"}
        )
        examples.append(
            {"answer": row["hallucinated_answer"], "sources": sources, "label": "hallucinated"}
        )
    return examples


def fetch_raw_rows(url: str = HALUEVAL_QA_URL) -> list[dict]:
    with urllib.request.urlopen(url) as response:
        text = response.read().decode("utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare a HaluEval QA benchmark subset.")
    parser.add_argument(
        "--limit", type=int, default=50, help="Number of source rows to convert (2 examples each)"
    )
    parser.add_argument("--output", type=Path, default=Path("data/halueval_qa_benchmark.jsonl"))
    args = parser.parse_args()

    raw_rows = fetch_raw_rows()
    examples = convert_halueval_rows(raw_rows, args.limit)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w") as f:
        for example in examples:
            f.write(json.dumps(example) + "\n")

    print(f"Wrote {len(examples)} examples ({args.limit} source rows) to {args.output}")


if __name__ == "__main__":
    main()
