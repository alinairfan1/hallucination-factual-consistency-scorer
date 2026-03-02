# Mistral Migration + Judge Quality Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Anthropic with Mistral AI as the scorer's LLM-judge provider, and harden judge quality (deterministic sampling, retry resilience, more precise prompts) so the scorer produces more reliable, competitive results — then validate with a real live benchmark run.

**Architecture:** `MistralJudge` replaces `AnthropicJudge` behind the exact same `Judge` protocol (`complete(system: str, user: str) -> str`) already used by `claims.py`, `entailment.py`, and `scoring.py` — no changes needed to the scoring pipeline itself, only to the client and its construction. The live HTTP endpoint (`main.py`) and benchmark CLI (`benchmark/cli.py`) both build their `Mistral` client through the same shared retry configuration.

**Tech Stack:** `mistralai>=2.7` Python SDK (`mistralai.client.Mistral`, `mistralai.client.utils.{RetryConfig,BackoffStrategy}`).

## Global Constraints

- No live network/API calls in automated tests — every test uses a fake/stub client object, matching the existing `AnthropicJudge` test precedent.
- This is a full replacement, not dual-provider support: remove the `anthropic` dependency and all Anthropic-specific code/tests once the cutover lands.
- `mistralai>=2.7` — this floor is what's actually installed and verified working in this environment (`mistralai==2.7.2`); its `Mistral` client lives at `mistralai.client.Mistral`, not the top-level package (verified directly against the installed SDK, since this version's import surface differs from older `mistralai` releases).
- `judge_model` default: `"mistral-large-latest"` (Mistral's flagship model, for best judge quality).
- Real API key goes only in `.env` (already gitignored via `hallucination-factual-consistency-scorer/.gitignore:10`) — never committed, never hardcoded.
- Every judge API call sets `temperature=0.0` for deterministic, reproducible verdicts.
- Every `Mistral` client construction (both `main.py` and `benchmark/cli.py`) uses a shared retry config covering `429/500/502/503/504` plus connection errors, so a single paid live benchmark run over ~100-300 calls survives transient API errors instead of falling through to the runner's fail-safe "hallucinated" label unnecessarily.

---

### Task 1: Add `MistralJudge` alongside the existing `AnthropicJudge`

**Files:**
- Modify: `src/scorer/llm_client.py`
- Test: `tests/test_llm_client.py`

**Interfaces:**
- Produces: `MistralJudge(model: str, client: Any)` with `.complete(system: str, user: str) -> str`, matching the `Judge` protocol already defined locally in `scoring.py`, `claims.py`, `entailment.py`, and `benchmark/runner.py`.
- Produces: `DEFAULT_JUDGE_RETRY_CONFIG: mistralai.client.utils.RetryConfig`, a module-level constant that Task 2 imports into both `main.py` and `benchmark/cli.py`.

This task is purely additive — `AnthropicJudge` stays in place and all its existing tests keep passing. Task 2 does the cutover.

- [ ] **Step 1: Write the failing tests for `MistralJudge`**

Append to `tests/test_llm_client.py` (keep all existing imports/classes/tests as-is, add these):

```python
from mistralai.client.utils import BackoffStrategy, RetryConfig

from scorer.llm_client import MistralJudge


@dataclass
class FakeMistralMessage:
    content: str


@dataclass
class FakeMistralChoice:
    message: FakeMistralMessage


@dataclass
class FakeMistralResponse:
    choices: list[FakeMistralChoice]


class FakeMistralChat:
    def __init__(self, response: FakeMistralResponse) -> None:
        self._response = response
        self.last_kwargs: dict | None = None

    def complete(self, **kwargs):
        self.last_kwargs = kwargs
        return self._response


class FakeMistralClient:
    def __init__(self, response: FakeMistralResponse) -> None:
        self.chat = FakeMistralChat(response)


def test_mistral_judge_extracts_message_content():
    fake_response = FakeMistralResponse(
        choices=[FakeMistralChoice(message=FakeMistralMessage(content="hello"))]
    )
    client = FakeMistralClient(fake_response)
    judge = MistralJudge(model="mistral-large-latest", client=client)

    result = judge.complete(system="Be terse.", user="Say hi.")

    assert result == "hello"


def test_mistral_judge_passes_system_user_model_and_temperature():
    fake_response = FakeMistralResponse(
        choices=[FakeMistralChoice(message=FakeMistralMessage(content="hi"))]
    )
    client = FakeMistralClient(fake_response)
    judge = MistralJudge(model="mistral-large-latest", client=client)

    judge.complete(system="Be terse.", user="Say hi.")

    assert client.chat.last_kwargs["model"] == "mistral-large-latest"
    assert client.chat.last_kwargs["temperature"] == 0.0
    assert client.chat.last_kwargs["messages"] == [
        {"role": "system", "content": "Be terse."},
        {"role": "user", "content": "Say hi."},
    ]


def test_default_judge_retry_config_covers_transient_errors():
    from scorer.llm_client import DEFAULT_JUDGE_RETRY_CONFIG

    assert isinstance(DEFAULT_JUDGE_RETRY_CONFIG, RetryConfig)
    assert DEFAULT_JUDGE_RETRY_CONFIG.strategy == "backoff"
    assert isinstance(DEFAULT_JUDGE_RETRY_CONFIG.backoff, BackoffStrategy)
    assert DEFAULT_JUDGE_RETRY_CONFIG.retry_connection_errors is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_llm_client.py -v -k "mistral"`
Expected: FAIL with `ImportError: cannot import name 'MistralJudge' from 'scorer.llm_client'` (and `DEFAULT_JUDGE_RETRY_CONFIG` missing).

- [ ] **Step 3: Install the Mistral SDK**

Run: `python3 -m pip install -e ".[dev]" "mistralai>=2.7"`
(This project has no committed venv; installing directly matches how earlier milestones set up dependencies in this environment.)

- [ ] **Step 4: Implement `MistralJudge` and the shared retry config**

Add to `src/scorer/llm_client.py` (keep the existing `AnthropicJudge` class and `parse_json_response` function untouched — just add these below them):

```python
from mistralai.client.utils import BackoffStrategy, RetryConfig

DEFAULT_JUDGE_RETRY_CONFIG = RetryConfig(
    "backoff",
    BackoffStrategy(500, 60_000, 1.5, 300_000),
    True,
)


class MistralJudge:
    def __init__(self, model: str, client: Any) -> None:
        self.model = model
        self.client = client

    def complete(self, system: str, user: str) -> str:
        response = self.client.chat.complete(
            model=self.model,
            temperature=0.0,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.choices[0].message.content
```

Move the `from mistralai.client.utils import BackoffStrategy, RetryConfig` import to the top of the file with the other imports (alongside `import json` and `from typing import Any`), not inline.

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_llm_client.py -v`
Expected: PASS (all tests, old `AnthropicJudge` tests and new `MistralJudge` tests)

- [ ] **Step 6: Run full verification**

Run: `ruff check . && mypy src && pytest -v`
Expected: all clean, all tests pass (nothing else in the codebase references `MistralJudge` yet, so this is a pure addition)

- [ ] **Step 7: Commit**

```bash
git add src/scorer/llm_client.py tests/test_llm_client.py pyproject.toml
git commit -m "feat: add MistralJudge alongside AnthropicJudge"
```

---

### Task 2: Cut over config, dependencies, and both entry points to Mistral; remove Anthropic

**Files:**
- Modify: `pyproject.toml`
- Modify: `src/scorer/config.py`
- Modify: `src/scorer/main.py`
- Modify: `src/scorer/benchmark/cli.py`
- Modify: `src/scorer/llm_client.py` (remove `AnthropicJudge`)
- Modify: `tests/test_llm_client.py` (remove `AnthropicJudge` tests/fakes)
- Modify: `tests/test_benchmark_cli.py`

**Interfaces:**
- Consumes: `MistralJudge` and `DEFAULT_JUDGE_RETRY_CONFIG` from `scorer.llm_client` (Task 1).
- Produces: `settings.mistral_api_key: str`, `settings.judge_model: str = "mistral-large-latest"` (renamed from `anthropic_api_key`); `get_llm_client() -> MistralJudge` in `main.py`; `build_judge() -> MistralJudge` in `benchmark/cli.py`. These two function names/signatures are unchanged from before (only their internal implementation and return type change), so `tests/test_score_endpoint.py` needs no changes — it only ever calls `app.dependency_overrides[get_llm_client] = lambda: fake_llm`, never the real implementation.

This is one atomic task because `config.py`, `main.py`, and `benchmark/cli.py` are mutually interdependent — renaming the settings field breaks both entry points simultaneously, so they must land together.

- [ ] **Step 1: Update `pyproject.toml` dependencies**

In `pyproject.toml`, replace:
```toml
    "anthropic>=0.40",
```
with:
```toml
    "mistralai>=2.7",
```

- [ ] **Step 2: Update `config.py`**

Replace the full contents of `src/scorer/config.py`:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SCORER_", env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./scorer.db"
    judge_model: str = "mistral-large-latest"
    mistral_api_key: str = ""


settings = Settings()
```

- [ ] **Step 3: Update `main.py`**

In `src/scorer/main.py`, replace:
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
```
with:
```python
from fastapi import Depends, FastAPI
from mistralai.client import Mistral
from sqlalchemy.orm import Session

from scorer.config import settings
from scorer.db.models import ScoringRun
from scorer.db.session import get_session
from scorer.llm_client import DEFAULT_JUDGE_RETRY_CONFIG, MistralJudge
from scorer.schemas import ScoreRequest, ScoreResponse
from scorer.scoring import run_scoring
```

And replace:
```python
def get_llm_client() -> AnthropicJudge:
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return AnthropicJudge(model=settings.judge_model, client=client)


@app.post("/v1/score", response_model=ScoreResponse)
def score(
    request: ScoreRequest,
    session: Session = Depends(get_session),
    llm: AnthropicJudge = Depends(get_llm_client),
) -> ScoreResponse:
```
with:
```python
def get_llm_client() -> MistralJudge:
    client = Mistral(api_key=settings.mistral_api_key, retry_config=DEFAULT_JUDGE_RETRY_CONFIG)
    return MistralJudge(model=settings.judge_model, client=client)


@app.post("/v1/score", response_model=ScoreResponse)
def score(
    request: ScoreRequest,
    session: Session = Depends(get_session),
    llm: MistralJudge = Depends(get_llm_client),
) -> ScoreResponse:
```

- [ ] **Step 4: Update `benchmark/cli.py`**

In `src/scorer/benchmark/cli.py`, replace:
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
```
with:
```python
import argparse
from pathlib import Path

from mistralai.client import Mistral

from scorer.benchmark.metrics import compute_calibration, compute_classification_metrics
from scorer.benchmark.report import format_report
from scorer.benchmark.runner import run_benchmark
from scorer.config import settings
from scorer.dataset import load_examples
from scorer.llm_client import DEFAULT_JUDGE_RETRY_CONFIG, MistralJudge

DEFAULT_DATASET_PATH = Path("data/halueval_qa_benchmark.jsonl")


def build_judge() -> MistralJudge:
    client = Mistral(api_key=settings.mistral_api_key, retry_config=DEFAULT_JUDGE_RETRY_CONFIG)
    return MistralJudge(model=settings.judge_model, client=client)
```

(`cli.py`'s `main()` function body is unchanged — it only calls `build_judge()`, it doesn't reference `AnthropicJudge`/`MistralJudge` by name.)

- [ ] **Step 5: Remove `AnthropicJudge` from `llm_client.py`**

Delete the `AnthropicJudge` class from `src/scorer/llm_client.py` (the `MistralJudge` class and `parse_json_response` function stay).

- [ ] **Step 6: Remove `AnthropicJudge` tests from `tests/test_llm_client.py`**

Delete `FakeContentBlock`, `FakeResponse`, `FakeAnthropicMessages`, `FakeAnthropicClient`, and the three `test_complete_*` functions that use them (`test_complete_extracts_text_content`, `test_complete_concatenates_multiple_text_blocks`, `test_complete_passes_system_user_and_model_correctly`). Keep the `MistralJudge` tests from Task 1 and the `parse_json_response` tests untouched. Remove the now-unused `from scorer.llm_client import AnthropicJudge, parse_json_response` import at the top and replace with `from scorer.llm_client import parse_json_response` (the `MistralJudge`/retry-config import from Task 1 stays as its own line).

- [ ] **Step 7: Update `tests/test_benchmark_cli.py`**

Replace:
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
```
with:
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
        def __init__(self, api_key: str, retry_config) -> None:
            self.api_key = api_key
            self.retry_config = retry_config

    monkeypatch.setattr(cli_module, "Mistral", FakeClient)

    judge = build_judge()

    assert judge.model == settings.judge_model
    assert judge.client.api_key == settings.mistral_api_key
```

(The rest of `test_benchmark_cli.py` — `test_main_prints_report_for_a_small_dataset` and its `FakeJudge` usage — is provider-agnostic and stays exactly as-is.)

- [ ] **Step 8: Reinstall dependencies to drop `anthropic`**

Run: `python3 -m pip install -e ".[dev]"`
Run: `python3 -m pip uninstall -y anthropic`

- [ ] **Step 9: Run full verification**

Run: `ruff check . && mypy src && pytest -v`
Expected: all clean, all tests pass, zero references to `anthropic`/`Anthropic` remain

Run: `grep -rn "anthropic\|Anthropic" src/ tests/ pyproject.toml`
Expected: no output

- [ ] **Step 10: Commit**

```bash
git add pyproject.toml src/scorer/config.py src/scorer/main.py src/scorer/benchmark/cli.py src/scorer/llm_client.py tests/test_llm_client.py tests/test_benchmark_cli.py
git commit -m "feat: cut over from Anthropic to Mistral as the judge provider"
```

---

### Task 3: Harden claim-extraction and entailment judge prompts

**Files:**
- Modify: `src/scorer/claims.py`
- Modify: `src/scorer/entailment.py`

**Interfaces:**
- No signature changes: `extract_claims(answer: str, llm: Judge) -> list[str]` and `check_entailment(claim: str, sources: list[str], llm: Judge) -> tuple[Verdict, str]` keep their exact existing signatures. Only the prompt constants change.

Existing tests in `tests/test_claims.py` and `tests/test_entailment.py` assert on parsing/behavior against canned fake responses, not prompt wording, so they're expected to keep passing unchanged — this task's regression check is the full suite, not new unit tests. Prompt-wording quality is empirically validated in Task 5's live benchmark run, not by a unit test.

- [ ] **Step 1: Replace `EXTRACTION_SYSTEM_PROMPT` in `claims.py`**

In `src/scorer/claims.py`, replace:
```python
EXTRACTION_SYSTEM_PROMPT = (
    "You are a claim extraction system. Given a piece of text, break it into a list "
    "of atomic, self-contained, independently-checkable factual claims. Each claim "
    "must stand alone: resolve pronouns and implicit references so no claim depends "
    "on another claim's context. Respond with ONLY a JSON array of strings (the "
    "claims), no other text. If the text contains no checkable factual claims, "
    "respond with []."
)
```
with:
```python
EXTRACTION_SYSTEM_PROMPT = (
    "You are a claim extraction system for a fact-checking pipeline. Given a piece "
    "of text, break it into a list of atomic, self-contained, independently-checkable "
    "factual claims.\n\n"
    "Rules:\n"
    "- Each claim must stand alone: resolve pronouns and implicit references so no "
    "claim depends on another claim's context.\n"
    "- Each claim must express exactly one fact. Split compound statements (e.g. "
    '"X and Y") into separate claims for X and for Y.\n'
    "- Preserve exact numbers, dates, units, and proper nouns verbatim — do not "
    'round, paraphrase, or drop precision (e.g. keep "330 meters", not "tall").\n'
    "- Do not extract subjective opinions, greetings, or statements with no factual "
    'content (e.g. "Hello!", "That\'s a great question.").\n'
    "- If the text contains no checkable factual claims, respond with [].\n\n"
    "Example:\n"
    'Text: "The Eiffel Tower, built in 1889, is 330 meters tall and located in '
    'Paris."\n'
    'Claims: ["The Eiffel Tower was built in 1889.", "The Eiffel Tower is 330 '
    'meters tall.", "The Eiffel Tower is located in Paris."]\n\n'
    "Respond with ONLY a JSON array of strings (the claims), no other text."
)
```

- [ ] **Step 2: Replace `ENTAILMENT_SYSTEM_PROMPT` in `entailment.py`**

In `src/scorer/entailment.py`, replace:
```python
ENTAILMENT_SYSTEM_PROMPT = (
    "You are a fact-checking judge. Given a CLAIM and a set of SOURCE documents, "
    "decide whether the claim is entailed (fully supported by the sources), "
    "contradicted (the sources say something inconsistent with it), or "
    "not_enough_info (the sources don't say enough to decide either way). Respond "
    "with ONLY a JSON object of the form: "
    '{"verdict": "entailed" | "contradicted" | "not_enough_info", '
    '"reason": "<one sentence explanation>"}.'
)
```
with:
```python
ENTAILMENT_SYSTEM_PROMPT = (
    "You are a rigorous fact-checking judge. Given a CLAIM and a set of SOURCE "
    "documents, decide whether the claim is entailed, contradicted, or "
    "not_enough_info with respect to the sources.\n\n"
    "Definitions:\n"
    "- entailed: the sources fully support the claim, including any specific "
    "numbers, dates, or names it contains.\n"
    "- contradicted: the sources state something inconsistent with the claim — "
    "this includes near-misses, like a number, date, or name in the claim differing "
    'from what the sources say (e.g. claim says "330 meters", sources say "324 '
    'meters").\n'
    "- not_enough_info: the sources simply do not address the claim at all, so "
    "there is nothing to confirm or deny.\n\n"
    "Judge only what the sources actually say — do not use outside/world knowledge "
    "to fill gaps, and do not give the claim the benefit of the doubt.\n\n"
    "Respond with ONLY a JSON object of the form: "
    '{"verdict": "entailed" | "contradicted" | "not_enough_info", '
    '"reason": "<one sentence explanation>"}.'
)
```

- [ ] **Step 3: Run full verification**

Run: `ruff check . && mypy src && pytest -v`
Expected: all clean, all existing tests still pass unchanged (regression proof that behavior didn't break)

- [ ] **Step 4: Commit**

```bash
git add src/scorer/claims.py src/scorer/entailment.py
git commit -m "improve: harden claim-extraction and entailment judge prompts"
```

---

### Task 4: Final whole-branch review

Review everything changed by Tasks 1–3 together (diff since the end of M3, commit `10c850d` or later — check `git log` for the exact M3-final commit hash before starting). Focus areas for the reviewer:

- No `anthropic`/`Anthropic` references remain anywhere in `src/`, `tests/`, or `pyproject.toml`.
- `MistralJudge.complete()` correctly sets `temperature=0.0` and builds the `messages` list in the right order (system, then user).
- `DEFAULT_JUDGE_RETRY_CONFIG` is actually wired into both `main.py`'s `get_llm_client()` and `benchmark/cli.py`'s `build_judge()` (not just defined and unused).
- `tests/test_score_endpoint.py` required zero changes and still passes (dependency-override architecture held up under the provider swap).
- The new prompt text in `claims.py`/`entailment.py` doesn't change either function's parsing/validation logic, only the prompt string constants.
- No real API key appears anywhere in tracked files (`git grep` for the literal key value should return nothing once `.env` exists in Task 5 — `.env` is gitignored).

Fix any findings with the usual dispatch-comprehensive-fix-subagent → re-verify cycle used for M1–M3.

---

### Task 5: Live benchmark validation + documentation (executed directly, not via a fresh subagent)

This task needs the real `MISTRAL_API_KEY` already present in `.env` and involves real paid API calls — it's executed directly rather than delegated, so the person running it can honestly interpret the actual output rather than have a subagent report on its own live run unsupervised.

**Files:**
- Create: `.env` (gitignored, never committed)
- Modify: `README.md`
- Modify: `PLANNING.md`

- [ ] **Step 1: Create `.env` with the real key**

Create `.env` in the project root:
```
SCORER_MISTRAL_API_KEY=<the real key>
```

- [ ] **Step 2: Run the live benchmark**

Run: `scorer-benchmark` (or `python3 -m scorer.benchmark.cli` if the console script isn't on PATH)
Record the actual printed report: total examples, precision, recall, F1, naive baseline F1, error count, and the calibration table.

- [ ] **Step 3: Sanity-check the numbers against the known ceiling**

Compare the real F1 against `data/README.md`'s documented ~73.7% length-heuristic ceiling. If real F1 doesn't clearly exceed that ceiling, that's a real finding to report honestly, not something to paper over — note it plainly in the README rather than omitting it.

- [ ] **Step 4: Update `README.md`**

Replace the `## Status` section's current text (which still says "M1 (scaffold) complete... that's M2", stale since M2/M3 shipped) with an accurate status reflecting M1–M3 complete plus the real benchmark numbers from Step 2, and note the provider is Mistral AI (`mistral-large-latest`), not Anthropic.

- [ ] **Step 5: Update `PLANNING.md`**

Check off the completed line in the `## 9. Best Practices Checklist`:
```
- [x] README documents real benchmark numbers (precision/recall/F1, calibration) once M3 lands
```

- [ ] **Step 6: Commit**

```bash
git add README.md PLANNING.md
git commit -m "docs: document real Mistral benchmark results"
```

(`.env` is not added — it's gitignored.)
