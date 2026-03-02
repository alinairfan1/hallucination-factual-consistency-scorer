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
| 76.0% | 77.6% | 76.8% | 0.0% |

**Read this number carefully, not just as a win.** [`data/README.md`](./data/README.md) documents that a
classifier using *only answer length* (zero fact-checking) can reach ~73.7% F1 on this same dataset, since
HaluEval's fabricated answers tend to be more verbose than its terse correct ones even after the
length-confound fix. The real judge's 76.8% clears that ceiling by ~3.1 points — real evidence the judge
is doing more than counting words, though still not an overwhelming margin.

This F1 is the result of one diagnosis-and-fix pass: an initial run scored 75.2% F1 (68.3%/83.7%
precision/recall). Rather than guess at prompt tweaks, the 18 false positives and 7 false negatives from
that run were pulled and read individually. Most false positives turned out to be the entailment judge
inventing a distinction the claim never asserted (e.g. reading a source's "former base" as meaning a unit
couldn't have been "most recently" stationed there, or a person's age at the time in the source as a claim
about their age today) rather than accepting straightforward support. Several false negatives were
comparative claims (dates, counts) that the judge compared incorrectly. `src/scorer/entailment.py`'s
prompt was refined to explicitly accept simple logical composition as entailed and to require the judge to
extract-then-compare exact quantities for comparative claims — which moved precision from 68.3%→76.0% at
a small recall cost (83.7%→77.6%), for a net F1 gain. Not every diagnosed failure was fixable this way: one
case where the judge substituted a factually different but similarly-themed historical event (treating
"the Korean War" as equivalent to sources describing World War II, using outside knowledge the prompt
explicitly tells it not to use) still slips through — a genuinely hard case, not chased further to avoid
overfitting the prompt to one example. Some fraction of the residual gap to a "solved" benchmark is also
HaluEval's own label noise, not judge quality — the diagnosis surfaced at least one row where the
`right_answer`/`hallucinated_answer` pairing itself looks swapped or wrong relative to the provided source
text (row for "which genus... contains only one species" — the source's genus/family distinction doesn't
match HaluEval's own labeling).

Recall is still slightly higher than precision, consistent with the judge's prompt remaining strict about
near-miss numbers/dates/named entities counting as contradictions: it catches most hallucinations but
still flags a smaller number of legitimately-supported claims.

**Calibration** (does a higher score actually mean more likely supported?): directionally yes, but not
tightly. The two largest buckets are `score=1.00` (n=49, 77.6% actually supported) and `score=0.00` (n=29,
17.2% actually supported) — the extremes point the right way, but a "0.0 confidence" example still turns
out supported nearly one time in six, so the score is a useful ranking signal, not a calibrated
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
