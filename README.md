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

M1 (scaffold) complete — FastAPI app, Pydantic schemas, `ScoringRun` DB model, dataset ingestion,
Alembic migrations, Docker Compose packaging, and CI are all in place. No claim-extraction or
entailment-checking logic yet — that's M2. See [`PLANNING.md`](./PLANNING.md) for full design and
[`docs/superpowers/plans/2026-07-26-m1-scaffold.md`](./docs/superpowers/plans/2026-07-26-m1-scaffold.md)
for the M1 implementation plan. Difficulty: ⭐⭐ Easy-Medium (2nd of 5 in build order).

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
