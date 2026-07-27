from dataclasses import dataclass, field
from typing import Literal, Protocol

from scorer.dataset import DatasetExample
from scorer.schemas import ClaimVerdict
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
    answer: str = ""
    sources: list[str] = field(default_factory=list)
    claims: list[ClaimVerdict] = field(default_factory=list)
    error: str | None = None


def run_benchmark(
    examples: list[DatasetExample], llm: Judge, threshold: float = 1.0
) -> list[QueryResult]:
    results = []
    for index, example in enumerate(examples):
        try:
            scored = run_scoring(example.answer, example.sources, llm)
        except Exception as exc:  # noqa: BLE001
            # A single malformed judge response — bad claim extraction/entailment
            # JSON (scorer.llm_client.parse_json_response, scorer.claims,
            # scorer.entailment) or an API-boundary failure that survives the
            # judge's own retry budget (timeout, connection error, SDK error) —
            # must not abort the whole benchmark run and discard every
            # already-computed result, especially on a paid multi-hundred-call
            # run. Record it as a distinguishable failure and keep going.
            #
            # predicted_label is set to "hallucinated" as a fail-safe default
            # so a broken judge response never silently counts as "supported"
            # for any code that reads QueryResult directly without checking
            # `error`. compute_classification_metrics excludes errored rows
            # from precision/recall/F1 entirely, so this fail-safe label does
            # not itself corrupt those numbers — it only protects callers that
            # don't go through compute_classification_metrics.
            results.append(
                QueryResult(
                    index=index,
                    actual_label=example.label,
                    predicted_label="hallucinated",
                    score=0.0,
                    num_flagged_claims=0,
                    answer=example.answer,
                    sources=example.sources,
                    error=str(exc),
                )
            )
            continue

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
                answer=example.answer,
                sources=example.sources,
                claims=scored.claims,
            )
        )
    return results
