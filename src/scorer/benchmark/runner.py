from dataclasses import dataclass
from typing import Literal, Protocol

from scorer.dataset import DatasetExample
from scorer.scoring import run_scoring


class Judge(Protocol):
    def complete(self, system: str, user: str) -> str: ...


@dataclass
class QueryResult:
    index: int
    actual_label: Literal["supported", "hallucinated"]
    predicted_label: Literal["supported", "hallucinated"]
    score: float
    num_flagged_claims: int


def run_benchmark(
    examples: list[DatasetExample], llm: Judge, threshold: float = 1.0
) -> list[QueryResult]:
    results = []
    for index, example in enumerate(examples):
        scored = run_scoring(example.answer, example.sources, llm)
        predicted_label: Literal["supported", "hallucinated"] = (
            "supported" if scored.score >= threshold else "hallucinated"
        )
        results.append(
            QueryResult(
                index=index,
                actual_label=example.label,
                predicted_label=predicted_label,
                score=scored.score,
                num_flagged_claims=len(scored.flagged_claims),
            )
        )
    return results
