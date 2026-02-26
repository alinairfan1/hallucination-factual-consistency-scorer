# M2 — Core Scoring Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire up the actual scoring decision: a database session factory, a minimal LLM-judge client, a claim-extraction module, a per-claim entailment checker, an aggregator, and a `POST /v1/score` endpoint that ties extraction → entailment → aggregation → DB logging → response envelope together.

**Architecture:** Five small, independently-testable modules (`db/session.py`, `llm_client.py`, `claims.py`, `entailment.py`, `aggregation.py`) composed together in `main.py`'s new endpoint. The only external network boundary (the Anthropic API) sits behind a minimal `AnthropicJudge` client and is injected via FastAPI `Depends`, so automated tests substitute a fake judge and never make a live network call. Unlike the sibling `cost-optimizing-llm-router` project, there is only one model tier here (a judge, not a router choosing between cheap/expensive models), so the client is a single concrete class with no adapter interface/ABC — that abstraction would have no second implementation to justify it.

**Tech Stack:** Builds on M1's FastAPI + SQLAlchemy + Postgres scaffold. Adds the `anthropic` Python SDK for the judge model.

## Global Constraints

- Reuse M1's interfaces verbatim — do not rename: `scorer.schemas.ScoreRequest`, `FlaggedClaim`, `ScoreResponse`; `scorer.db.models.ScoringRun` (fields `answer`, `num_sources`, `score`, `num_flagged_claims`); `scorer.config.settings`.
- No new Postgres migration in this milestone — `scoring_runs` schema from M1 is unchanged.
- Secrets: the Anthropic API key is read only via `SCORER_ANTHROPIC_API_KEY` (pydantic-settings env var), never hardcoded.
- Automated tests must never make a live network call to any LLM provider. The LLM-judge boundary is always faked/injected in tests. A manual live check against a real provider is optional, attempted only if `ANTHROPIC_API_KEY` (or `SCORER_ANTHROPIC_API_KEY`) is present in the shell environment, and is never required for a task to pass.
- Judge model for this project: `claude-sonnet-5` (per PLANNING.md's tech stack decision to use an LLM-judge baseline for MVP; this is a judge/reasoning task, so it uses the same higher-quality tier the sibling router project reserves for its "expensive" path — not the cheap/fast tier).
- `FlaggedClaim.verdict` stays at its M1 type, `Literal["contradicted", "not_enough_info"]` (do not widen it to include `"entailed"` — entailed claims are never flagged). The wider 3-way verdict (`entailed` / `contradicted` / `not_enough_info`) is an internal type used by the entailment checker and aggregator only, per PLANNING.md §6.
- Aggregate scoring formula for this milestone (per PLANNING.md §3's "aggregate scoring: weighted combination of per-claim entailment results into a single 0-1 confidence score"): `score = entailed_count / total_claims`, with a vacuous score of `1.0` and an empty flagged list when there are zero extracted claims (nothing to contradict). `contradicted` and `not_enough_info` are weighted identically (both simply non-entailed) for this MVP score — a different weighting between the two, or a calibration pass, is out of scope for M2 (calibration is an explicit stretch feature in PLANNING.md §3/§7).
- No new claim-extraction/entailment code should introduce a second LLM client abstraction, ABC, or provider-swapping mechanism — YAGNI, there is one judge model in this milestone.
- Source layout: continue using `src/scorer/` (src-layout), tests under `tests/`.

---

### Task 1: Database session factory

**Files:**
- Create: `src/scorer/db/session.py`
- Test: `tests/test_session.py`

**Interfaces:**
- Consumes: `scorer.config.settings.database_url` (M1), `scorer.db.base.Base`, `scorer.db.models.ScoringRun` (M1).
- Produces:
  - `scorer.db.session.make_session_factory(database_url: str) -> sessionmaker` — builds an engine + sessionmaker for a given URL.
  - `scorer.db.session.SessionLocal` — the module-level sessionmaker bound to `settings.database_url`.
  - `scorer.db.session.get_session() -> Generator[Session, None, None]` — FastAPI dependency yielding a session, closing it afterward. This exact function is what Task 6's endpoint and tests will import and override.

- [ ] **Step 1: Write the failing test**

Create `tests/test_session.py`:

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from scorer.db import session as session_module
from scorer.db.base import Base
from scorer.db.models import ScoringRun
from scorer.db.session import get_session


def test_get_session_yields_a_working_session(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    test_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(session_module, "SessionLocal", test_factory)

    gen = get_session()
    db = next(gen)
    db.add(
        ScoringRun(
            answer="Paris is the capital of France.",
            num_sources=1,
            score=1.0,
            num_flagged_claims=0,
        )
    )
    db.commit()
    assert db.query(ScoringRun).count() == 1

    gen.close()  # must not raise


def test_make_session_factory_builds_a_working_sessionmaker():
    factory = session_module.make_session_factory("sqlite:///:memory:")
    Base.metadata.create_all(factory().get_bind())

    with factory() as db:
        db.add(
            ScoringRun(
                answer="The Eiffel Tower is in Berlin.",
                num_sources=1,
                score=0.0,
                num_flagged_claims=1,
            )
        )
        db.commit()
        assert db.query(ScoringRun).count() == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_session.py -v`
Expected: FAIL/ERROR with `ModuleNotFoundError: No module named 'scorer.db.session'`.

- [ ] **Step 3: Write minimal implementation**

Create `src/scorer/db/session.py`:

```python
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from scorer.config import settings


def make_session_factory(database_url: str) -> sessionmaker:
    engine = create_engine(database_url)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


SessionLocal = make_session_factory(settings.database_url)


def get_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_session.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add src/scorer/db/session.py tests/test_session.py
git commit -m "feat: add database session factory"
```

---

### Task 2: LLM-judge client and JSON response parsing

**Files:**
- Create: `src/scorer/llm_client.py`
- Test: `tests/test_llm_client.py`

**Interfaces:**
- Consumes: nothing new (the Anthropic SDK's response shape, duck-typed — no import of the real `anthropic` package needed here; that dependency is added in Task 6).
- Produces:
  - `scorer.llm_client.AnthropicJudge` — `__init__(self, model: str, client: Any)`; `client` is duck-typed against the Anthropic SDK's `.messages.create(...)` interface, injected by the caller (Task 6 constructs the real `anthropic.Anthropic()` client; tests inject a fake). Method `complete(self, system: str, user: str) -> str` sends one system+user turn and returns the concatenated text content of the response.
  - `scorer.llm_client.parse_json_response(text: str) -> Any` — strips a leading/trailing ```` ``` ```` or ` ```json` code fence if present, then `json.loads`s the result. Raises `ValueError` with the raw (unstripped) `text` embedded in the message if the content is not valid JSON. Tasks 3 and 4 both use this to parse the judge's structured replies.

- [ ] **Step 1: Write the failing test**

Create `tests/test_llm_client.py`:

```python
from dataclasses import dataclass

import pytest

from scorer.llm_client import AnthropicJudge, parse_json_response


@dataclass
class FakeContentBlock:
    type: str
    text: str


@dataclass
class FakeResponse:
    content: list[FakeContentBlock]


class FakeAnthropicMessages:
    def __init__(self, response: FakeResponse) -> None:
        self._response = response
        self.last_kwargs: dict | None = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        return self._response


class FakeAnthropicClient:
    def __init__(self, response: FakeResponse) -> None:
        self.messages = FakeAnthropicMessages(response)


def test_complete_extracts_text_content():
    fake_response = FakeResponse(content=[FakeContentBlock(type="text", text="hello")])
    client = FakeAnthropicClient(fake_response)
    judge = AnthropicJudge(model="claude-sonnet-5", client=client)

    result = judge.complete(system="Be terse.", user="Say hi.")

    assert result == "hello"


def test_complete_concatenates_multiple_text_blocks():
    fake_response = FakeResponse(
        content=[
            FakeContentBlock(type="text", text="hel"),
            FakeContentBlock(type="text", text="lo"),
        ]
    )
    client = FakeAnthropicClient(fake_response)
    judge = AnthropicJudge(model="claude-sonnet-5", client=client)

    assert judge.complete(system="sys", user="usr") == "hello"


def test_complete_passes_system_user_and_model_correctly():
    fake_response = FakeResponse(content=[FakeContentBlock(type="text", text="hi")])
    client = FakeAnthropicClient(fake_response)
    judge = AnthropicJudge(model="claude-sonnet-5", client=client)

    judge.complete(system="Be terse.", user="Say hi.")

    assert client.messages.last_kwargs["system"] == "Be terse."
    assert client.messages.last_kwargs["messages"] == [{"role": "user", "content": "Say hi."}]
    assert client.messages.last_kwargs["model"] == "claude-sonnet-5"


def test_parse_json_response_parses_plain_json():
    assert parse_json_response('{"a": 1}') == {"a": 1}


def test_parse_json_response_strips_markdown_fence_with_json_tag():
    assert parse_json_response('```json\n{"a": 1}\n```') == {"a": 1}


def test_parse_json_response_strips_plain_markdown_fence():
    assert parse_json_response('```\n["one", "two"]\n```') == ["one", "two"]


def test_parse_json_response_raises_clear_error_for_invalid_json():
    with pytest.raises(ValueError) as exc_info:
        parse_json_response("not json")
    assert "not json" in str(exc_info.value)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_llm_client.py -v`
Expected: FAIL/ERROR with `ModuleNotFoundError: No module named 'scorer.llm_client'`.

- [ ] **Step 3: Write minimal implementation**

Create `src/scorer/llm_client.py`:

```python
import json
from typing import Any


class AnthropicJudge:
    def __init__(self, model: str, client: Any) -> None:
        self.model = model
        self.client = client

    def complete(self, system: str, user: str) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(block.text for block in response.content if block.type == "text")


def parse_json_response(text: str) -> Any:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`").strip()
        if stripped.startswith("json"):
            stripped = stripped[len("json") :].strip()

    try:
        return json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Expected valid JSON from the LLM, got: {text!r}") from exc
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_llm_client.py -v`
Expected: PASS (7 passed).

- [ ] **Step 5: Commit**

```bash
git add src/scorer/llm_client.py tests/test_llm_client.py
git commit -m "feat: add LLM-judge client and JSON response parsing"
```

---

### Task 3: Claim extraction

**Files:**
- Create: `src/scorer/claims.py`
- Test: `tests/test_claims.py`

**Interfaces:**
- Consumes: `scorer.llm_client.parse_json_response` (Task 2). Does not import `AnthropicJudge` directly — takes any object with a `complete(system: str, user: str) -> str` method (structural typing; tests use a local fake, not `AnthropicJudge`).
- Produces: `scorer.claims.extract_claims(answer: str, llm) -> list[str]` — sends `answer` to the judge with a structured extraction prompt and returns the parsed list of atomic claim strings. This exact signature is what Task 6's endpoint imports.

- [ ] **Step 1: Write the failing test**

Create `tests/test_claims.py`:

```python
import pytest

from scorer.claims import extract_claims


class FakeJudge:
    def __init__(self, response_text: str) -> None:
        self.response_text = response_text
        self.last_system: str | None = None
        self.last_user: str | None = None

    def complete(self, system: str, user: str) -> str:
        self.last_system = system
        self.last_user = user
        return self.response_text


def test_extract_claims_parses_json_array():
    llm = FakeJudge('["Paris is the capital of France.", "The tower is 330m tall."]')

    claims = extract_claims(
        "Paris is the capital of France and the tower is 330m tall.", llm
    )

    assert claims == ["Paris is the capital of France.", "The tower is 330m tall."]


def test_extract_claims_passes_answer_as_user_message():
    llm = FakeJudge("[]")

    extract_claims("some answer", llm)

    assert llm.last_user == "some answer"


def test_extract_claims_returns_empty_list_for_no_claims():
    llm = FakeJudge("[]")

    assert extract_claims("Hello!", llm) == []


def test_extract_claims_raises_for_non_list_response():
    llm = FakeJudge('{"not": "a list"}')

    with pytest.raises(ValueError):
        extract_claims("some answer", llm)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_claims.py -v`
Expected: FAIL/ERROR with `ModuleNotFoundError: No module named 'scorer.claims'`.

- [ ] **Step 3: Write minimal implementation**

Create `src/scorer/claims.py`:

```python
from typing import Protocol

from scorer.llm_client import parse_json_response


class Judge(Protocol):
    def complete(self, system: str, user: str) -> str: ...


EXTRACTION_SYSTEM_PROMPT = (
    "You are a claim extraction system. Given a piece of text, break it into a list "
    "of atomic, self-contained, independently-checkable factual claims. Each claim "
    "must stand alone: resolve pronouns and implicit references so no claim depends "
    "on another claim's context. Respond with ONLY a JSON array of strings (the "
    "claims), no other text. If the text contains no checkable factual claims, "
    "respond with []."
)


def extract_claims(answer: str, llm: Judge) -> list[str]:
    response_text = llm.complete(system=EXTRACTION_SYSTEM_PROMPT, user=answer)
    claims = parse_json_response(response_text)

    if not isinstance(claims, list):
        raise ValueError(f"Expected a JSON array of claims, got: {response_text!r}")

    return [str(claim) for claim in claims]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_claims.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add src/scorer/claims.py tests/test_claims.py
git commit -m "feat: add claim extraction module"
```

---

### Task 4: Entailment checker

**Files:**
- Create: `src/scorer/entailment.py`
- Test: `tests/test_entailment.py`

**Interfaces:**
- Consumes: `scorer.llm_client.parse_json_response` (Task 2); the same structural `Judge` protocol as Task 3 (a `complete(system: str, user: str) -> str` method) — do not import `scorer.claims.Judge`, redefine locally, matching Task 3's approach of a small local `Protocol` per module rather than a shared cross-module import for this structural type.
- Produces:
  - `scorer.entailment.Verdict` — `Literal["entailed", "contradicted", "not_enough_info"]`. This is the *wider* 3-way type; `scorer.schemas.FlaggedClaim.verdict` (M1) stays the narrower 2-value `Literal["contradicted", "not_enough_info"]` and never sees `"entailed"`.
  - `scorer.entailment.check_entailment(claim: str, sources: list[str], llm: Judge) -> tuple[Verdict, str]` — sends the claim and sources to the judge with a structured entailment prompt, returns `(verdict, reason)`. This exact signature is what Task 5 (aggregation) and Task 6 (endpoint) rely on.

- [ ] **Step 1: Write the failing test**

Create `tests/test_entailment.py`:

```python
import pytest

from scorer.entailment import check_entailment


class FakeJudge:
    def __init__(self, response_text: str) -> None:
        self.response_text = response_text
        self.last_system: str | None = None
        self.last_user: str | None = None

    def complete(self, system: str, user: str) -> str:
        self.last_system = system
        self.last_user = user
        return self.response_text


def test_check_entailment_returns_entailed_verdict_and_reason():
    llm = FakeJudge('{"verdict": "entailed", "reason": "Directly stated in the source."}')

    verdict, reason = check_entailment(
        "Paris is the capital of France.",
        ["Paris is the capital of France."],
        llm,
    )

    assert verdict == "entailed"
    assert reason == "Directly stated in the source."


def test_check_entailment_returns_contradicted_verdict():
    llm = FakeJudge('{"verdict": "contradicted", "reason": "Sources say Paris, not Berlin."}')

    verdict, reason = check_entailment(
        "The Eiffel Tower is in Berlin.",
        ["The Eiffel Tower is in Paris."],
        llm,
    )

    assert verdict == "contradicted"


def test_check_entailment_returns_not_enough_info_verdict():
    llm = FakeJudge('{"verdict": "not_enough_info", "reason": "Sources do not mention height."}')

    verdict, reason = check_entailment(
        "The tower is 330 meters tall.",
        ["The tower is located in Paris."],
        llm,
    )

    assert verdict == "not_enough_info"


def test_check_entailment_includes_claim_and_sources_in_user_message():
    llm = FakeJudge('{"verdict": "entailed", "reason": "ok"}')

    check_entailment("The sky is blue.", ["The sky appears blue.", "Water is wet."], llm)

    assert "The sky is blue." in llm.last_user
    assert "The sky appears blue." in llm.last_user
    assert "Water is wet." in llm.last_user


def test_check_entailment_raises_for_missing_fields():
    llm = FakeJudge('{"verdict": "entailed"}')

    with pytest.raises(ValueError):
        check_entailment("claim", ["source"], llm)


def test_check_entailment_raises_for_unexpected_verdict_value():
    llm = FakeJudge('{"verdict": "maybe", "reason": "unsure"}')

    with pytest.raises(ValueError):
        check_entailment("claim", ["source"], llm)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_entailment.py -v`
Expected: FAIL/ERROR with `ModuleNotFoundError: No module named 'scorer.entailment'`.

- [ ] **Step 3: Write minimal implementation**

Create `src/scorer/entailment.py`:

```python
from typing import Literal, Protocol

from scorer.llm_client import parse_json_response

Verdict = Literal["entailed", "contradicted", "not_enough_info"]

_VALID_VERDICTS = {"entailed", "contradicted", "not_enough_info"}


class Judge(Protocol):
    def complete(self, system: str, user: str) -> str: ...


ENTAILMENT_SYSTEM_PROMPT = (
    "You are a fact-checking judge. Given a CLAIM and a set of SOURCE documents, "
    "decide whether the claim is entailed (fully supported by the sources), "
    "contradicted (the sources say something inconsistent with it), or "
    "not_enough_info (the sources don't say enough to decide either way). Respond "
    "with ONLY a JSON object of the form: "
    '{"verdict": "entailed" | "contradicted" | "not_enough_info", '
    '"reason": "<one sentence explanation>"}.'
)


def check_entailment(claim: str, sources: list[str], llm: Judge) -> tuple[Verdict, str]:
    sources_block = "\n".join(f"- {source}" for source in sources)
    user_prompt = f"CLAIM: {claim}\n\nSOURCES:\n{sources_block}"

    response_text = llm.complete(system=ENTAILMENT_SYSTEM_PROMPT, user=user_prompt)
    parsed = parse_json_response(response_text)

    if not isinstance(parsed, dict) or "verdict" not in parsed or "reason" not in parsed:
        raise ValueError(
            f"Expected a JSON object with 'verdict' and 'reason', got: {response_text!r}"
        )

    verdict = parsed["verdict"]
    if verdict not in _VALID_VERDICTS:
        raise ValueError(f"Unexpected verdict {verdict!r}, expected one of {_VALID_VERDICTS}")

    return verdict, str(parsed["reason"])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_entailment.py -v`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add src/scorer/entailment.py tests/test_entailment.py
git commit -m "feat: add entailment checker"
```

---

### Task 5: Aggregation

**Files:**
- Create: `src/scorer/aggregation.py`
- Test: `tests/test_aggregation.py`

**Interfaces:**
- Consumes: `scorer.entailment.Verdict` (Task 4), `scorer.schemas.FlaggedClaim` (M1).
- Produces: `scorer.aggregation.aggregate(claim_verdicts: list[tuple[str, Verdict, str]]) -> tuple[float, list[FlaggedClaim]]` — each input tuple is `(claim, verdict, reason)`. Returns `(score, flagged_claims)` where `score = entailed_count / len(claim_verdicts)`, or `1.0` with an empty list when `claim_verdicts` is empty. `flagged_claims` contains one `FlaggedClaim` per non-entailed tuple, in input order. This exact signature is what Task 6's endpoint imports.

**Implementation note:** build `flagged_claims` with an explicit `for` loop using `if verdict == "entailed": continue`, not a list comprehension. mypy narrows `verdict: Verdict` (a 3-value `Literal`) to the remaining 2-value `Literal` after that early `continue`, which is required for `FlaggedClaim(verdict=verdict, ...)` to type-check against `FlaggedClaim.verdict`'s narrower `Literal["contradicted", "not_enough_info"]`. A list-comprehension filter (`if verdict != "entailed"`) does not get the same mypy narrowing and will fail `mypy src`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_aggregation.py`:

```python
from scorer.aggregation import aggregate
from scorer.schemas import FlaggedClaim


def test_aggregate_empty_list_returns_vacuous_full_score():
    score, flagged = aggregate([])

    assert score == 1.0
    assert flagged == []


def test_aggregate_all_entailed_returns_score_one_and_no_flags():
    claim_verdicts = [
        ("claim one", "entailed", "supported by source"),
        ("claim two", "entailed", "supported by source"),
    ]

    score, flagged = aggregate(claim_verdicts)

    assert score == 1.0
    assert flagged == []


def test_aggregate_mixed_verdicts_computes_fraction_and_flags_non_entailed():
    claim_verdicts = [
        ("claim one", "entailed", "supported"),
        ("claim two", "contradicted", "sources disagree"),
        ("claim three", "not_enough_info", "sources are silent"),
        ("claim four", "entailed", "supported"),
    ]

    score, flagged = aggregate(claim_verdicts)

    assert score == 0.5
    assert flagged == [
        FlaggedClaim(claim="claim two", verdict="contradicted", reason="sources disagree"),
        FlaggedClaim(
            claim="claim three", verdict="not_enough_info", reason="sources are silent"
        ),
    ]


def test_aggregate_all_contradicted_returns_score_zero():
    claim_verdicts = [("claim", "contradicted", "false")]

    score, flagged = aggregate(claim_verdicts)

    assert score == 0.0
    assert len(flagged) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_aggregation.py -v`
Expected: FAIL/ERROR with `ModuleNotFoundError: No module named 'scorer.aggregation'`.

- [ ] **Step 3: Write minimal implementation**

Create `src/scorer/aggregation.py`:

```python
from scorer.entailment import Verdict
from scorer.schemas import FlaggedClaim


def aggregate(claim_verdicts: list[tuple[str, Verdict, str]]) -> tuple[float, list[FlaggedClaim]]:
    if not claim_verdicts:
        return 1.0, []

    entailed_count = sum(1 for _, verdict, _ in claim_verdicts if verdict == "entailed")
    score = entailed_count / len(claim_verdicts)

    flagged_claims: list[FlaggedClaim] = []
    for claim, verdict, reason in claim_verdicts:
        if verdict == "entailed":
            continue
        flagged_claims.append(FlaggedClaim(claim=claim, verdict=verdict, reason=reason))

    return score, flagged_claims
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_aggregation.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add src/scorer/aggregation.py tests/test_aggregation.py
git commit -m "feat: add per-claim verdict aggregation"
```

---

### Task 6: Wire up POST /v1/score

**Files:**
- Modify: `pyproject.toml` (add `anthropic` dependency)
- Modify: `src/scorer/config.py` (replace entire contents)
- Modify: `src/scorer/main.py` (replace entire contents)
- Test: `tests/test_score_endpoint.py`

**Interfaces:**
- Consumes: `scorer.claims.extract_claims` (Task 3), `scorer.entailment.check_entailment` (Task 4), `scorer.aggregation.aggregate` (Task 5), `scorer.llm_client.AnthropicJudge` (Task 2), `scorer.db.session.get_session` (Task 1), `scorer.db.models.ScoringRun`, `scorer.schemas.ScoreRequest`/`ScoreResponse` (all M1/M2 prior tasks).
- Produces: `POST /v1/score` endpoint; `scorer.main.get_llm_client` — a FastAPI dependency function, overridable in tests via `app.dependency_overrides`.

**Implementation note:** build `claim_verdicts` with an explicit `for` loop that unpacks `check_entailment`'s `tuple[Verdict, str]` into two named locals before appending a 3-tuple, not a list-comprehension with `(claim, *check_entailment(...))`. This keeps the constructed tuple's type precisely `tuple[str, Verdict, str]` for `aggregate` (Task 5) rather than relying on mypy's inference of a starred-unpack inside a tuple display.

- [ ] **Step 1: Add the `anthropic` dependency**

In `pyproject.toml`, in the `[project]` `dependencies` list, add `"anthropic>=0.40",` after the existing `"psycopg[binary]>=3.2",` line.

Run: `pip install -e ".[dev]"`
Expected: install succeeds, `anthropic` package now importable.

- [ ] **Step 2: Write the failing test**

Create `tests/test_score_endpoint.py`:

```python
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from scorer.db.base import Base
from scorer.db.models import ScoringRun
from scorer.db.session import get_session
from scorer.main import app, get_llm_client


class FakeJudge:
    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self.calls: list[tuple[str, str]] = []

    def complete(self, system: str, user: str) -> str:
        self.calls.append((system, user))
        return self._responses.pop(0)


def _override_session(test_factory):
    def _get_session():
        session = test_factory()
        try:
            yield session
        finally:
            session.close()

    return _get_session


def test_score_endpoint_fully_supported_answer_returns_score_one():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    test_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    fake_llm = FakeJudge(
        responses=[
            '["Paris is the capital of France."]',
            '{"verdict": "entailed", "reason": "Directly stated in the source."}',
        ]
    )

    app.dependency_overrides[get_session] = _override_session(test_factory)
    app.dependency_overrides[get_llm_client] = lambda: fake_llm

    try:
        client = TestClient(app)
        response = client.post(
            "/v1/score",
            json={
                "answer": "Paris is the capital of France.",
                "sources": ["Paris is the capital of France."],
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["score"] == 1.0
        assert body["flagged_claims"] == []

        with test_factory() as session:
            logged = session.query(ScoringRun).one()
            assert logged.answer == "Paris is the capital of France."
            assert logged.num_sources == 1
            assert logged.score == 1.0
            assert logged.num_flagged_claims == 0
    finally:
        app.dependency_overrides.clear()


def test_score_endpoint_contradicted_claim_is_flagged():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    test_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    fake_llm = FakeJudge(
        responses=[
            '["The Eiffel Tower is in Berlin."]',
            '{"verdict": "contradicted", "reason": "Sources say Paris, not Berlin."}',
        ]
    )

    app.dependency_overrides[get_session] = _override_session(test_factory)
    app.dependency_overrides[get_llm_client] = lambda: fake_llm

    try:
        client = TestClient(app)
        response = client.post(
            "/v1/score",
            json={
                "answer": "The Eiffel Tower is in Berlin.",
                "sources": ["The Eiffel Tower is in Paris."],
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["score"] == 0.0
        assert len(body["flagged_claims"]) == 1
        assert body["flagged_claims"][0]["verdict"] == "contradicted"

        with test_factory() as session:
            logged = session.query(ScoringRun).one()
            assert logged.score == 0.0
            assert logged.num_flagged_claims == 1
    finally:
        app.dependency_overrides.clear()


def test_score_endpoint_no_claims_extracted_logs_vacuous_score():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    test_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    fake_llm = FakeJudge(responses=["[]"])

    app.dependency_overrides[get_session] = _override_session(test_factory)
    app.dependency_overrides[get_llm_client] = lambda: fake_llm

    try:
        client = TestClient(app)
        response = client.post(
            "/v1/score",
            json={"answer": "Hello!", "sources": ["irrelevant source"]},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["score"] == 1.0
        assert body["flagged_claims"] == []
    finally:
        app.dependency_overrides.clear()
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/test_score_endpoint.py -v`
Expected: FAIL — `/v1/score` doesn't exist yet (404), or `ImportError` for `get_llm_client` (not yet defined in `scorer.main`).

- [ ] **Step 4: Write minimal implementation**

Replace the entire contents of `src/scorer/config.py`:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SCORER_", env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./scorer.db"
    judge_model: str = "claude-sonnet-5"
    anthropic_api_key: str = ""


settings = Settings()
```

Replace the entire contents of `src/scorer/main.py`:

```python
import anthropic
from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session

from scorer.aggregation import aggregate
from scorer.claims import extract_claims
from scorer.config import settings
from scorer.db.models import ScoringRun
from scorer.db.session import get_session
from scorer.entailment import check_entailment
from scorer.llm_client import AnthropicJudge
from scorer.schemas import ScoreRequest, ScoreResponse

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
    claims = extract_claims(request.answer, llm)

    claim_verdicts = []
    for claim in claims:
        verdict, reason = check_entailment(claim, request.sources, llm)
        claim_verdicts.append((claim, verdict, reason))

    score_value, flagged_claims = aggregate(claim_verdicts)

    log = ScoringRun(
        answer=request.answer,
        num_sources=len(request.sources),
        score=score_value,
        num_flagged_claims=len(flagged_claims),
    )
    session.add(log)
    session.commit()

    return ScoreResponse(score=score_value, flagged_claims=flagged_claims)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_score_endpoint.py -v`
Expected: PASS (3 passed).

Then run the full suite: `pytest -v`
Expected: all tests across every module pass (M1's 9 tests plus M2's new tests).

- [ ] **Step 6: Optional manual live check**

If `ANTHROPIC_API_KEY` is set in your shell environment, you may manually verify the real judge path works end-to-end:

```bash
SCORER_ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" uvicorn scorer.main:app --port 8000 &
sleep 2
curl -s -X POST http://localhost:8000/v1/score \
  -H "Content-Type: application/json" \
  -d '{"answer": "The Eiffel Tower is in Berlin.", "sources": ["The Eiffel Tower is a wrought-iron tower in Paris, France."]}'
kill %1
```

Expected: a JSON response with `score` well below `1.0` and a non-empty `flagged_claims` list whose verdict is `"contradicted"` (Berlin vs. Paris is a direct contradiction). If `ANTHROPIC_API_KEY` is not set, skip this step entirely and note it as skipped in your report — it is not required for the task to be DONE.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml src/scorer/config.py src/scorer/main.py tests/test_score_endpoint.py
git commit -m "feat: wire claim extraction, entailment, and aggregation into POST /v1/score"
```

---

## Plan-Level Verification

After all 6 tasks are complete:
1. `pytest -v` — all tests across every test file pass (M1's 9 tests plus M2's new tests across `test_session.py`, `test_llm_client.py`, `test_claims.py`, `test_entailment.py`, `test_aggregation.py`, `test_score_endpoint.py`).
2. `ruff check .` and `mypy src` both exit 0 — in particular, confirm Task 5's aggregation loop (not a comprehension) satisfies mypy's `Literal` narrowing.
3. `git log --oneline` shows 6 new commits (one per task; Task 6 is a single commit) on top of M1's history.
4. `POST /v1/score` is reachable and returns a real score + flagged-claims list for both a fully-supported answer and a contradicted one (exercised by the automated tests; optionally confirmed live per Task 6 Step 6).
