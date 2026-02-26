# M3 — Benchmark Harness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract M2's scoring logic into a pure, reusable function; acquire and commit a real, licensed subset of a public hallucination-labeled dataset; and build a benchmark CLI that replays that subset through the scorer, computing precision/recall/F1 against human labels plus a calibration check, per PLANNING.md §7's evaluation plan.

**Architecture:** A pure `scorer.scoring.run_scoring()` (extracted from `main.py`'s endpoint) becomes the single seam both the live API and the offline benchmark call — the endpoint wraps it with DB logging, the benchmark runner calls it directly with no DB writes. A small `scorer.benchmark` subpackage (`runner.py`, `metrics.py`, `report.py`, `cli.py`) replays a committed dataset file through `run_scoring`, scores classification metrics against the dataset's ground-truth labels, and prints a report. A top-level `scripts/` package (mirroring the sibling `cost-optimizing-llm-router` project's own `scripts/` convention) holds the one-time dataset conversion tool that produced the committed subset. The only external network boundaries are the Anthropic API (isolated behind the existing `AnthropicJudge`, faked in every automated test) and the one-time GitHub fetch of the public dataset (run once during Task 2, not part of the app's runtime).

**Tech Stack:** Builds on M1/M2's FastAPI + SQLAlchemy + Postgres + `AnthropicJudge` stack. No new third-party dependencies — dataset fetching uses the stdlib `urllib.request`, matching the sibling router project's stdlib-only benchmark tooling.

## Global Constraints

- Reuse M1/M2 interfaces verbatim: `scorer.schemas.ScoreResponse`/`FlaggedClaim`, `scorer.dataset.DatasetExample`/`load_examples`, `scorer.claims.extract_claims`, `scorer.entailment.check_entailment`/`Verdict`, `scorer.aggregation.aggregate`, `scorer.llm_client.AnthropicJudge`/`parse_json_response`, `scorer.config.settings`.
- Task 1's refactor must not change `scorer.main`'s `POST /v1/score` behavior — the existing M2 endpoint tests (`tests/test_score_endpoint.py`) must pass unmodified after the refactor.
- No new Postgres migration, and no writes to `scoring_runs` from the benchmark path — the benchmark CLI is an offline tool producing a report, entirely separate from the live API's request logging (mirrors the sibling router project's own M3 constraint).
- Automated tests must never make a live network call to any LLM provider. The benchmark runner/CLI tests always inject a fake judge via the same `complete(system, user) -> str` structural interface established in M2. A manual live run of the CLI against a real Anthropic API is optional, attempted only if `ANTHROPIC_API_KEY` is present in the shell environment, and never required for a task to pass.
- Dataset acquisition (fetching the real public HaluEval subset) IS a required part of Task 2 — unlike the optional LLM live-check, the committed `data/halueval_qa_benchmark.jsonl` file must actually exist with real converted data for this milestone to be complete, since M3's "working" bar (PLANNING.md §7) is precision/recall/F1 against real human-labeled ground truth, not synthetic data. This requires one live network fetch to GitHub during Task 2's implementation (not per-test-run, and not part of the app's runtime).
- Dataset choice: the HaluEval QA subset ([RUCAIBox/HaluEval](https://github.com/RUCAIBox/HaluEval), MIT License) — chosen because its schema (`knowledge`, `question`, `right_answer`, `hallucinated_answer`) maps 1:1 onto `scorer.dataset.DatasetExample`'s shape, and its MIT license permits redistributing a subset in this repo (per PLANNING.md §9's "dataset license/usage terms checked and documented" checklist item).
- Subset size: convert the first 50 source rows into 100 `DatasetExample` entries (50 `"supported"` + 50 `"hallucinated"`) — large enough for a meaningful precision/recall/F1 signal, small enough to keep a live benchmark run's LLM API cost and runtime modest.
- Predicted label derivation: `predicted_label = "supported" if score >= threshold else "hallucinated"`, default `threshold = 1.0` (i.e., any flagged claim predicts `"hallucinated"`) — each dataset example is built from a single `right_answer`/`hallucinated_answer` sentence, so this is expected to behave close to binary in practice. Per-claim partial-credit thresholds are a stretch/calibration refinement (PLANNING.md §3 Stretch), not M3 MVP.
- Calibration groups results by exact `score` value rather than fixed-width bins — appropriate given scores are naturally near-discrete for this single-claim-per-example dataset (documented inline in Task 4's implementation).
- Naive baseline ("always predict supported") F1 is computed directly: `0.0` whenever the dataset contains at least one actual `"hallucinated"` example (recall is 0 in that case), `1.0` only in the degenerate all-`"supported"` case — per PLANNING.md §7's "F1 clearly above a naive baseline like 'always say supported'".
- Source layout: continue `src/scorer/` (src-layout); a new `src/scorer/benchmark/` subpackage for benchmark-only modules (mirrors the sibling router project's `router.benchmark` subpackage); one-time dataset-prep tooling lives in a top-level `scripts/` package (mirrors the sibling project's own `scripts/` convention) with `tests/conftest.py` adding the repo root to `sys.path` so tests can `from scripts... import ...`.

---

### Task 1: Extract pure scoring function

**Files:**
- Create: `src/scorer/scoring.py`
- Modify: `src/scorer/main.py`
- Test: `tests/test_scoring.py`

**Interfaces:**
- Consumes: `scorer.claims.extract_claims`, `scorer.entailment.check_entailment`, `scorer.aggregation.aggregate`, `scorer.schemas.ScoreResponse` (all M2/M1).
- Produces: `scorer.scoring.run_scoring(answer: str, sources: list[str], llm) -> ScoreResponse` — the exact extract→entail→aggregate composition currently inline in `main.py`'s `score()` route, moved to a pure, DB-free function. `llm` is any object with a `complete(system: str, user: str) -> str` method (same structural typing as `scorer.claims.Judge`/`scorer.entailment.Judge`). This exact signature is what Task 3's benchmark runner imports and calls directly (no HTTP, no DB) — the reason this extraction is happening now, per the M2 final-review's forward-looking suggestion.

- [ ] **Step 1: Write the failing test**

Create `tests/test_scoring.py`:

```python
from scorer.scoring import run_scoring


class FakeJudge:
    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)

    def complete(self, system: str, user: str) -> str:
        return self._responses.pop(0)


def test_run_scoring_fully_supported_answer_returns_score_one():
    llm = FakeJudge(
        responses=[
            '["Paris is the capital of France."]',
            '{"verdict": "entailed", "reason": "Directly stated in the source."}',
        ]
    )

    result = run_scoring(
        "Paris is the capital of France.", ["Paris is the capital of France."], llm
    )

    assert result.score == 1.0
    assert result.flagged_claims == []


def test_run_scoring_contradicted_claim_is_flagged():
    llm = FakeJudge(
        responses=[
            '["The Eiffel Tower is in Berlin."]',
            '{"verdict": "contradicted", "reason": "Sources say Paris, not Berlin."}',
        ]
    )

    result = run_scoring(
        "The Eiffel Tower is in Berlin.", ["The Eiffel Tower is in Paris."], llm
    )

    assert result.score == 0.0
    assert len(result.flagged_claims) == 1
    assert result.flagged_claims[0].verdict == "contradicted"


def test_run_scoring_no_claims_returns_vacuous_score():
    llm = FakeJudge(responses=["[]"])

    result = run_scoring("Hello!", ["irrelevant source"], llm)

    assert result.score == 1.0
    assert result.flagged_claims == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_scoring.py -v`
Expected: FAIL/ERROR with `ModuleNotFoundError: No module named 'scorer.scoring'`.

- [ ] **Step 3: Write minimal implementation**

Create `src/scorer/scoring.py`:

```python
from typing import Protocol

from scorer.aggregation import aggregate
from scorer.claims import extract_claims
from scorer.entailment import check_entailment
from scorer.schemas import ScoreResponse


class Judge(Protocol):
    def complete(self, system: str, user: str) -> str: ...


def run_scoring(answer: str, sources: list[str], llm: Judge) -> ScoreResponse:
    claims = extract_claims(answer, llm)

    claim_verdicts = []
    for claim in claims:
        verdict, reason = check_entailment(claim, sources, llm)
        claim_verdicts.append((claim, verdict, reason))

    score_value, flagged_claims = aggregate(claim_verdicts)
    return ScoreResponse(score=score_value, flagged_claims=flagged_claims)
```

Replace the body of `src/scorer/main.py`'s `score()` function (keep everything else in the file — imports, `app`, `health()`, `get_llm_client()` — unchanged) so the full file reads:

```python
import anthropic
from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session

from scorer.config import settings
from scorer.db.models import ScoringRun
from scorer.db.session import get_session
from scorer.llm_client import AnthropicJudge
from scorer.schemas import ScoreRequest, ScoreResponse
from scorer.scoring import run_scoring

app = FastAPI(title="Hallucination / Factual-Consistency Scorer")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def get_llm_client() -> AnthropicJudge:
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return AnthropicJudge(model=settings.judge_model, client=client)


@app.post("/v1/score", response_model=ScoreResponse)
def score(
    request: ScoreRequest,
    session: Session = Depends(get_session),
    llm: AnthropicJudge = Depends(get_llm_client),
) -> ScoreResponse:
    result = run_scoring(request.answer, request.sources, llm)

    log = ScoringRun(
        answer=request.answer,
        num_sources=len(request.sources),
        score=result.score,
        num_flagged_claims=len(result.flagged_claims),
    )
    session.add(log)
    session.commit()

    return result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_scoring.py -v`
Expected: PASS (3 passed).

Then run the existing M2 endpoint tests to confirm the refactor didn't change behavior: `pytest tests/test_score_endpoint.py -v`
Expected: PASS (3 passed), unmodified from M2.

- [ ] **Step 5: Commit**

```bash
git add src/scorer/scoring.py src/scorer/main.py tests/test_scoring.py
git commit -m "refactor: extract pure run_scoring function from the /v1/score endpoint"
```

---

### Task 2: Acquire and commit a real HaluEval QA benchmark subset

**Files:**
- Create: `scripts/__init__.py`
- Create: `scripts/prepare_halueval_subset.py`
- Create: `tests/conftest.py`
- Test: `tests/test_prepare_halueval_subset.py`
- Create (generated by running the script, not hand-written): `data/halueval_qa_benchmark.jsonl`
- Create: `data/README.md`

**Interfaces:**
- Produces:
  - `scripts.prepare_halueval_subset.convert_halueval_rows(raw_rows: list[dict], limit: int) -> list[dict]` — pure function, no network. Takes parsed HaluEval QA rows (`{"knowledge": str, "question": str, "right_answer": str, "hallucinated_answer": str}`) and returns a flat list of `scorer.dataset.DatasetExample`-shaped dicts (`{"answer": str, "sources": list[str], "label": "supported" | "hallucinated"}`), two per input row, capped at `limit` input rows. This is what Task 3's runner tests can reuse for fixture data if needed, and is the function this task's automated test actually exercises.
  - `scripts.prepare_halueval_subset.fetch_raw_rows(url: str) -> list[dict]` — network I/O, not unit-tested (mirrors the sibling project's own `build_adapters()`-style pattern of leaving the live network call thin and untested, per that project's precedent).
  - `scripts.prepare_halueval_subset.main() -> None` — CLI entrypoint: fetches, converts, writes JSONL to `--output` (default `data/halueval_qa_benchmark.jsonl`).
  - `data/halueval_qa_benchmark.jsonl` — the committed output of actually running this script once against the real HaluEval dataset (100 lines: 50 `"supported"` + 50 `"hallucinated"`), in the exact JSONL shape `scorer.dataset.load_examples` (M1) already parses.
  - `data/README.md` — documents the dataset's source, license (MIT, RUCAIBox/HaluEval), and how `data/halueval_qa_benchmark.jsonl` was generated.

- [ ] **Step 1: Add `tests/conftest.py` so `scripts` is importable in tests**

Create `tests/conftest.py`:

```python
import sys
from pathlib import Path

# Add root directory to Python path so the top-level `scripts` package is importable
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))
```

- [ ] **Step 2: Write the failing test**

Create `tests/test_prepare_halueval_subset.py`:

```python
from scripts.prepare_halueval_subset import convert_halueval_rows


def test_convert_halueval_rows_produces_two_examples_per_row():
    raw_rows = [
        {
            "knowledge": "Paris is the capital of France.",
            "question": "What is the capital of France?",
            "right_answer": "Paris is the capital of France.",
            "hallucinated_answer": "Berlin is the capital of France.",
        }
    ]

    examples = convert_halueval_rows(raw_rows, limit=10)

    assert len(examples) == 2
    assert examples[0] == {
        "answer": "Paris is the capital of France.",
        "sources": ["Paris is the capital of France."],
        "label": "supported",
    }
    assert examples[1] == {
        "answer": "Berlin is the capital of France.",
        "sources": ["Paris is the capital of France."],
        "label": "hallucinated",
    }


def test_convert_halueval_rows_respects_limit():
    raw_rows = [
        {"knowledge": "k1", "question": "q1", "right_answer": "r1", "hallucinated_answer": "h1"},
        {"knowledge": "k2", "question": "q2", "right_answer": "r2", "hallucinated_answer": "h2"},
        {"knowledge": "k3", "question": "q3", "right_answer": "r3", "hallucinated_answer": "h3"},
    ]

    examples = convert_halueval_rows(raw_rows, limit=2)

    assert len(examples) == 4  # 2 rows * 2 examples each


def test_convert_halueval_rows_handles_empty_input():
    assert convert_halueval_rows([], limit=50) == []
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/test_prepare_halueval_subset.py -v`
Expected: FAIL/ERROR with `ModuleNotFoundError: No module named 'scripts'`.

- [ ] **Step 4: Write minimal implementation**

Create `scripts/__init__.py` (zero bytes).

Create `scripts/prepare_halueval_subset.py`:

```python
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
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_prepare_halueval_subset.py -v`
Expected: PASS (3 passed).

- [ ] **Step 6: Run the script for real to generate the committed dataset**

This step requires network access to GitHub. Run from the repo root:

```bash
PYTHONPATH=src python3 -m scripts.prepare_halueval_subset --limit 50 --output data/halueval_qa_benchmark.jsonl
```

Expected: prints `Wrote 100 examples (50 source rows) to data/halueval_qa_benchmark.jsonl`, and `data/halueval_qa_benchmark.jsonl` now exists with exactly 100 lines.

Verify the file's shape is loadable by M1's existing dataset loader:

```bash
python3 -c "
from pathlib import Path
from scorer.dataset import load_examples
examples = load_examples(Path('data/halueval_qa_benchmark.jsonl'))
print(len(examples), examples[0].label, examples[1].label)
"
```

Expected: `100 supported hallucinated` (each source row contributes one `supported` example immediately followed by one `hallucinated` example).

- [ ] **Step 7: Document dataset provenance and license**

Create `data/README.md`:

```markdown
# Benchmark dataset

`halueval_qa_benchmark.jsonl` is derived from the QA subset of
[HaluEval](https://github.com/RUCAIBox/HaluEval) (RUCAIBox), MIT License.

Each of the first 50 rows of HaluEval's `data/qa_data.json` was converted into
two examples in this project's `scorer.dataset.DatasetExample` JSONL shape
(`answer`, `sources`, `label`):

- `label: "supported"` — HaluEval's `right_answer` for that row, grounded
  against HaluEval's `knowledge` field as the single source.
- `label: "hallucinated"` — HaluEval's `hallucinated_answer` for the same row,
  grounded against the same `knowledge` source.

100 examples total (50 supported, 50 hallucinated). Regenerate with:

```bash
PYTHONPATH=src python3 -m scripts.prepare_halueval_subset --limit 50 --output data/halueval_qa_benchmark.jsonl
```

See HaluEval's repository for the original dataset and its MIT license terms.
```

- [ ] **Step 8: Commit**

```bash
git add scripts/__init__.py scripts/prepare_halueval_subset.py tests/conftest.py tests/test_prepare_halueval_subset.py data/halueval_qa_benchmark.jsonl data/README.md
git commit -m "feat: add HaluEval QA benchmark subset and conversion script"
```

---

### Task 3: Benchmark runner

**Files:**
- Create: `src/scorer/benchmark/__init__.py`
- Create: `src/scorer/benchmark/runner.py`
- Test: `tests/test_benchmark_runner.py`

**Interfaces:**
- Consumes: `scorer.dataset.DatasetExample` (M1), `scorer.scoring.run_scoring` (Task 1).
- Produces:
  - `scorer.benchmark.runner.QueryResult` — dataclass with `index: int`, `actual_label: Literal["supported", "hallucinated"]`, `predicted_label: Literal["supported", "hallucinated"]`, `score: float`, `num_flagged_claims: int`.
  - `scorer.benchmark.runner.run_benchmark(examples: list[DatasetExample], llm, threshold: float = 1.0) -> list[QueryResult]` — for each example (in order), calls `run_scoring(example.answer, example.sources, llm)`, derives `predicted_label = "supported" if score >= threshold else "hallucinated"`, and records the result. `llm` is the same structural `complete(system, user) -> str` type as Task 1's `Judge`. This exact signature is what Task 6's CLI imports and calls.

- [ ] **Step 1: Write the failing test**

Create `tests/test_benchmark_runner.py`:

```python
from scorer.benchmark.runner import QueryResult, run_benchmark
from scorer.dataset import DatasetExample


class FakeJudge:
    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)

    def complete(self, system: str, user: str) -> str:
        return self._responses.pop(0)


def test_run_benchmark_produces_one_result_per_example():
    examples = [
        DatasetExample(answer="a1", sources=["s1"], label="supported"),
        DatasetExample(answer="a2", sources=["s2"], label="hallucinated"),
    ]
    llm = FakeJudge(
        responses=[
            '["claim1"]',
            '{"verdict": "entailed", "reason": "ok"}',
            '["claim2"]',
            '{"verdict": "contradicted", "reason": "no"}',
        ]
    )

    results = run_benchmark(examples, llm)

    assert len(results) == 2
    assert all(isinstance(r, QueryResult) for r in results)


def test_run_benchmark_predicts_supported_when_score_meets_threshold():
    examples = [DatasetExample(answer="a1", sources=["s1"], label="supported")]
    llm = FakeJudge(responses=['["claim1"]', '{"verdict": "entailed", "reason": "ok"}'])

    results = run_benchmark(examples, llm, threshold=1.0)

    assert results[0].predicted_label == "supported"
    assert results[0].score == 1.0
    assert results[0].actual_label == "supported"


def test_run_benchmark_predicts_hallucinated_when_score_below_threshold():
    examples = [DatasetExample(answer="a1", sources=["s1"], label="hallucinated")]
    llm = FakeJudge(responses=['["claim1"]', '{"verdict": "contradicted", "reason": "no"}'])

    results = run_benchmark(examples, llm, threshold=1.0)

    assert results[0].predicted_label == "hallucinated"
    assert results[0].score == 0.0
    assert results[0].num_flagged_claims == 1


def test_run_benchmark_preserves_example_order_via_index():
    examples = [
        DatasetExample(answer="a1", sources=["s1"], label="supported"),
        DatasetExample(answer="a2", sources=["s2"], label="supported"),
    ]
    llm = FakeJudge(
        responses=[
            '["c1"]',
            '{"verdict": "entailed", "reason": "ok"}',
            '["c2"]',
            '{"verdict": "entailed", "reason": "ok"}',
        ]
    )

    results = run_benchmark(examples, llm)

    assert [r.index for r in results] == [0, 1]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_benchmark_runner.py -v`
Expected: FAIL/ERROR with `ModuleNotFoundError: No module named 'scorer.benchmark'`.

- [ ] **Step 3: Write minimal implementation**

Create `src/scorer/benchmark/__init__.py` (zero bytes).

Create `src/scorer/benchmark/runner.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_benchmark_runner.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add src/scorer/benchmark/__init__.py src/scorer/benchmark/runner.py tests/test_benchmark_runner.py
git commit -m "feat: add benchmark runner"
```

---

### Task 4: Classification metrics and calibration

**Files:**
- Create: `src/scorer/benchmark/metrics.py`
- Test: `tests/test_benchmark_metrics.py`

**Interfaces:**
- Consumes: `scorer.benchmark.runner.QueryResult` (Task 3).
- Produces:
  - `scorer.benchmark.metrics.ClassificationMetrics` — dataclass with `precision: float`, `recall: float`, `f1: float`, `naive_baseline_f1: float`.
  - `scorer.benchmark.metrics.compute_classification_metrics(results: list[QueryResult]) -> ClassificationMetrics` — positive class is `"hallucinated"`. `naive_baseline_f1` models "always predict supported": `0.0` if any result's `actual_label == "hallucinated"` (recall is 0), else `1.0`.
  - `scorer.benchmark.metrics.CalibrationBucket` — dataclass with `score: float`, `count: int`, `empirical_supported_rate: float`.
  - `scorer.benchmark.metrics.compute_calibration(results: list[QueryResult]) -> list[CalibrationBucket]` — groups results by their exact `score` value (not fixed-width bins — appropriate here since scores are naturally near-discrete for this single-claim-per-example dataset), sorted ascending by score, reporting what fraction of each group is actually `"supported"`. This exact pair of functions is what Task 5's report formatter and Task 6's CLI import.

- [ ] **Step 1: Write the failing test**

Create `tests/test_benchmark_metrics.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_benchmark_metrics.py -v`
Expected: FAIL/ERROR with `ModuleNotFoundError: No module named 'scorer.benchmark.metrics'`.

- [ ] **Step 3: Write minimal implementation**

Create `src/scorer/benchmark/metrics.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_benchmark_metrics.py -v`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add src/scorer/benchmark/metrics.py tests/test_benchmark_metrics.py
git commit -m "feat: add classification metrics and calibration"
```

---

### Task 5: Report formatting

**Files:**
- Create: `src/scorer/benchmark/report.py`
- Test: `tests/test_benchmark_report.py`

**Interfaces:**
- Consumes: `scorer.benchmark.metrics.ClassificationMetrics`/`CalibrationBucket` (Task 4).
- Produces: `scorer.benchmark.report.format_report(metrics: ClassificationMetrics, calibration: list[CalibrationBucket], num_examples: int) -> str` — a formatted, human-readable report. This exact signature is what Task 6's CLI imports and prints.

- [ ] **Step 1: Write the failing test**

Create `tests/test_benchmark_report.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_benchmark_report.py -v`
Expected: FAIL/ERROR with `ModuleNotFoundError: No module named 'scorer.benchmark.report'`.

- [ ] **Step 3: Write minimal implementation**

Create `src/scorer/benchmark/report.py`:

```python
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
        "",
        "Calibration (score -> empirical supported rate):",
    ]
    for bucket in calibration:
        lines.append(
            f"  score={bucket.score:.2f}  n={bucket.count:<4}  "
            f"empirical_supported_rate={bucket.empirical_supported_rate:.1%}"
        )
    return "\n".join(lines)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_benchmark_report.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add src/scorer/benchmark/report.py tests/test_benchmark_report.py
git commit -m "feat: add benchmark report formatting"
```

---

### Task 6: Benchmark CLI

**Files:**
- Create: `src/scorer/benchmark/cli.py`
- Modify: `pyproject.toml` (add `[project.scripts]` entry point)
- Test: `tests/test_benchmark_cli.py`

**Interfaces:**
- Consumes: `scorer.benchmark.runner.run_benchmark` (Task 3), `scorer.benchmark.metrics.compute_classification_metrics`/`compute_calibration` (Task 4), `scorer.benchmark.report.format_report` (Task 5), `scorer.dataset.load_examples` (M1), `scorer.llm_client.AnthropicJudge` (M2), `scorer.config.settings` (M1/M2).
- Produces:
  - `scorer.benchmark.cli.build_judge() -> AnthropicJudge` — constructs the real `anthropic.Anthropic` client and an `AnthropicJudge` from `settings`.
  - `scorer.benchmark.cli.main() -> None` — argparse entrypoint: parses `--dataset` (default `data/halueval_qa_benchmark.jsonl`) and `--threshold` (default `1.0`), loads examples, calls `build_judge()`, runs the benchmark, and prints the formatted report.
  - A console-script entry point `scorer-benchmark` in `pyproject.toml` pointing at `scorer.benchmark.cli:main`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_benchmark_cli.py`:

```python
from scorer.benchmark import cli as cli_module
from scorer.benchmark.cli import build_judge, main
from scorer.config import settings


class FakeJudge:
    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)

    def complete(self, system: str, user: str) -> str:
        return self._responses.pop(0)


def test_build_judge_uses_configured_model_and_key(monkeypatch):
    class FakeClient:
        def __init__(self, api_key: str) -> None:
            self.api_key = api_key

    monkeypatch.setattr(cli_module.anthropic, "Anthropic", FakeClient)

    judge = build_judge()

    assert judge.model == settings.judge_model
    assert judge.client.api_key == settings.anthropic_api_key


def test_main_prints_report_for_a_small_dataset(monkeypatch, tmp_path, capsys):
    dataset_path = tmp_path / "mini.jsonl"
    dataset_path.write_text(
        '{"answer": "Paris is the capital of France.", '
        '"sources": ["Paris is the capital of France."], "label": "supported"}\n'
        '{"answer": "Berlin is the capital of France.", '
        '"sources": ["Paris is the capital of France."], "label": "hallucinated"}\n'
    )

    fake_judge = FakeJudge(
        responses=[
            '["Paris is the capital of France."]',
            '{"verdict": "entailed", "reason": "ok"}',
            '["Berlin is the capital of France."]',
            '{"verdict": "contradicted", "reason": "no"}',
        ]
    )
    monkeypatch.setattr(cli_module, "build_judge", lambda: fake_judge)
    monkeypatch.setattr("sys.argv", ["scorer-benchmark", "--dataset", str(dataset_path)])

    main()

    captured = capsys.readouterr()
    assert "2 examples" in captured.out
    assert "Precision" in captured.out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_benchmark_cli.py -v`
Expected: FAIL/ERROR with `ModuleNotFoundError: No module named 'scorer.benchmark.cli'`.

- [ ] **Step 3: Write minimal implementation**

In `pyproject.toml`, add a new top-level table after `[project.optional-dependencies]` (before `[build-system]`):

```toml
[project.scripts]
scorer-benchmark = "scorer.benchmark.cli:main"
```

Create `src/scorer/benchmark/cli.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pip install -e ".[dev]"` (to register the new console script)
Run: `pytest tests/test_benchmark_cli.py -v`
Expected: PASS (2 passed).

Then run the full suite: `pytest -v`
Expected: all tests across every module pass (M1's 9 + M2's 26 + M3's new tests).

- [ ] **Step 5: Optional manual live check**

If `ANTHROPIC_API_KEY` is set in your shell environment, you may manually run the real benchmark end-to-end against the full committed dataset:

```bash
SCORER_ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" scorer-benchmark
```

Expected: a report with `100 examples`, precision/recall/F1 lines, and a calibration section. This makes real Anthropic API calls (roughly 100-300 calls depending on claim counts) and will incur real cost — only run this if you intend to spend that. If `ANTHROPIC_API_KEY` is not set, or you'd rather not spend the API cost, skip this step entirely and note it as skipped in your report — it is not required for the task to be DONE.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml src/scorer/benchmark/cli.py tests/test_benchmark_cli.py
git commit -m "feat: add benchmark CLI"
```

---

## Plan-Level Verification

After all 6 tasks are complete:
1. `pytest -v` — all tests across every test file pass (M1 + M2 + M3 combined).
2. `ruff check .` and `mypy src` both exit 0.
3. `git log --oneline` shows 6 new commits on top of M2's history.
4. `data/halueval_qa_benchmark.jsonl` exists, has 100 lines, and loads cleanly via `scorer.dataset.load_examples`.
5. `scorer-benchmark --threshold 1.0` (or `python -m scorer.benchmark.cli`) is runnable and prints a precision/recall/F1 + calibration report — exercised by the automated fake-judge tests; optionally confirmed live per Task 6 Step 5 when `ANTHROPIC_API_KEY` is available.
