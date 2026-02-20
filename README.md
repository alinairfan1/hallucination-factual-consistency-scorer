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

Planned — see [`PLANNING.md`](./PLANNING.md) for full design. Difficulty: ⭐⭐ Easy-Medium (2nd of 5 in build order).

## Quickstart

_Not yet implemented. Quickstart instructions will be added once the initial scaffold lands._
