# Hallucination / Factual-Consistency Scorer

## Problem

Every company shipping a RAG product hits the same unsolved-enough pain point: the model's answer sounds
right, cites the right-ish sources, and is still subtly wrong. There's no cheap, reliable way to check
whether an LLM's answer is actually supported by the documents it was given.

## Solution

Given an LLM's answer and the source documents it was supposedly grounded in, output a confidence score
(and the specific unsupported claims, if any) on whether the answer is actually backed by the sources —
benchmarked against a public hallucination dataset so the score means something, not just a vibe.

## Key Features

- Claim extraction from a free-text LLM answer
- Per-claim entailment check against the provided source documents
- Aggregate confidence score + list of flagged unsupported/contradicted claims
- Benchmarked precision/recall against a public hallucination-labeled dataset

## Tech Stack

Python (FastAPI), an NLI/entailment approach (LLM-judge baseline first, cheaper trained/heuristic scorer
as a stretch goal), Postgres for eval run storage, TypeScript + React for a results/report viewer, Docker.

## Status

M1–M3 complete — FastAPI app, Pydantic schemas, `ScoringRun` DB model, Docker Compose packaging, CI,
claim extraction, LLM-judge entailment checking, aggregate scoring, and a benchmark CLI against a real
HaluEval QA subset are all in place. The judge provider is **Mistral AI** (`mistral-large-latest`), not
Anthropic — see `src/scorer/llm_client.py`. M4 (report viewer) and M5 (polish) are not started. See
[`PLANNING.md`](./PLANNING.md) for full design and [`docs/superpowers/plans/`](./docs/superpowers/plans/)
for each milestone's implementation plan. Difficulty: ⭐⭐ Easy-Medium (2nd of 5 in build order).

### Real benchmark results

Run live against Mistral (`mistral-large-latest`) over the 100-example HaluEval QA subset in
[`data/halueval_qa_benchmark.jsonl`](./data/halueval_qa_benchmark.jsonl) (99 scored, 1 excluded for
malformed judge output):

| Precision | Recall | F1 | Naive "always supported" baseline |
|-----------|--------|-----|------------------------------------|
| 68.3% | 83.7% | 75.2% | 0.0% |

**Read this number carefully, not just as a win.** [`data/README.md`](./data/README.md) documents that a
classifier using *only answer length* (zero fact-checking) can reach ~73.7% F1 on this same dataset, since
HaluEval's fabricated answers tend to be more verbose than its terse correct ones even after the
length-confound fix. The real judge's 75.2% clears that ceiling by only ~1.5 points — real evidence the
judge is doing more than counting words, but not a decisive margin. Recall is noticeably higher than
precision, consistent with the judge's prompt (`src/scorer/entailment.py`) being deliberately strict about
near-miss numbers/dates counting as contradictions and not giving claims the benefit of the doubt: it
catches most hallucinations but also flags some legitimately-supported claims.

**Calibration** (does a higher score actually mean more likely supported?): directionally yes, but not
tightly. The two largest buckets are `score=1.00` (n=39, 79.5% actually supported) and `score=0.00` (n=35,
28.6% actually supported) — the extremes point the right way, but a "0.0 confidence" example still turns
out supported more than a quarter of the time, so the score is a useful ranking signal, not a calibrated
probability. Full per-score breakdown is printed by the CLI. Reproduce with:

```bash
scorer-benchmark
```

## Quickstart

Run the API + Postgres stack:

```bash
docker compose up -d --build
curl http://localhost:8000/health
# {"status":"ok"}
```

Run tests locally:

```bash
pip install -e ".[dev]"
pytest -v
```
