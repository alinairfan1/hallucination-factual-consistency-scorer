# PLANNING.md — Hallucination / Factual-Consistency Scorer

## 1. Overview & Motivation

RAG products are shipping everywhere, and the failure mode that actually hurts users isn't "the model
refused" — it's "the model answered confidently and cited plausible-looking sources, but the answer
isn't actually supported by them." Every company doing RAG in production has this problem and mostly
handles it with spot-checks or nothing. A scorer that takes (answer, sources) and returns a calibrated
confidence + flagged unsupported claims is a real, reusable piece of infrastructure — and unlike a demo
chatbot, it's evaluable against ground truth, which makes it a much stronger portfolio signal.

## 2. Difficulty Rating & Rationale

**⭐⭐ Easy-Medium** — chosen as project #2 in the build order.

- Still a single contained service (answer + sources in, score + flags out), no live infra to operate.
- Slightly harder than the router because claim extraction and evidence-matching have real linguistic
  edge cases (partial support, implied claims, numeric mismatches) rather than a simple threshold policy.
- Directly benchmarkable against an existing public hallucination dataset, so — like the router — there's
  no need to hand-build a labeled dataset from scratch.

## 3. Core Features (MVP) vs Stretch Features

**MVP**
- `POST /v1/score` endpoint: accepts `{answer, sources[]}`, returns `{score, flagged_claims[]}`
- Claim extraction: split the answer into atomic, checkable claims
- Entailment check per claim: LLM-judge baseline (structured prompt: "is this claim entailed by these
  sources? entailed / contradicted / not enough info") against the source set
- Aggregate scoring: weighted combination of per-claim entailment results into a single 0–1 confidence
  score, plus the explicit list of unsupported/contradicted claims
- Benchmark CLI: run the scorer over a public hallucination dataset, report precision/recall/F1 against
  human labels

**Stretch**
- Cheaper non-LLM scorer (trained NLI model, e.g. a small cross-encoder) as an alternative to the
  LLM-judge baseline, with a benchmark comparing cost vs accuracy between the two approaches
- Source-span highlighting: point to the exact sentence(s) in the sources that support/contradict a claim
- Calibration pass: verify that a "0.9 confidence" claim is actually correct ~90% of the time, adjust
  scoring to match
- Report viewer (React) showing side-by-side answer/sources with claims highlighted by verdict

## 4. Architecture

```
Client → Scorer API (FastAPI)
             │
             ├─ Claim Extractor (LLM call: answer → list of atomic claims)
             │
             ├─ Entailment Checker (per claim: LLM-judge against sources,
             │                       or NLI model in the stretch path)
             │
             ├─ Aggregator (per-claim verdicts → single confidence score + flagged list)
             │
             └─ Logger → Postgres (scoring runs, for benchmark analysis)

Benchmark CLI → loads public hallucination dataset (answer, sources, human labels)
              → runs each example through Scorer API
              → compares scorer output to human labels
              → reports precision/recall/F1, writes report
```

## 5. Tech Stack

- **Backend**: Python, FastAPI, Pydantic
- **Entailment**: LLM-judge (structured prompt + provider API call) for MVP; scikit-learn/small
  cross-encoder NLI model as the stretch alternative
- **Storage**: Postgres (scoring runs, benchmark results)
- **Dataset handling**: a public hallucination-labeled dataset (e.g. a RAG-hallucination benchmark such
  as RAGTruth or HaluEval, or a subset), loaded via a small ingestion script
- **Report viewer**: TypeScript + React
- **Packaging**: Docker Compose (API + Postgres + report viewer)

## 6. Key Technical Challenges

1. **Claim segmentation** — splitting an answer into atomic, independently-checkable claims without
   losing context (e.g. pronouns referring back to earlier claims). Solve with a structured extraction
   prompt that requires each claim to be self-contained, and spot-check extraction quality manually
   against a small sample before trusting it at scale.
2. **Partial support vs full support** — a claim can be half-right. Solve by using a 3-way verdict
   (entailed / contradicted / not-enough-info) per claim rather than a binary, and being explicit in the
   aggregate score about how partial support is weighted.
3. **Calibration of the confidence score** — a score is only useful if it means what it says. Solve by
   running a calibration check against the benchmark's human labels (does 0.8 confidence correspond to
   ~80% actual correctness?) and reporting that as part of the benchmark output, not just precision/recall.

## 7. Benchmark / Evaluation Plan

- Dataset: a public hallucination-labeled dataset with (answer, source documents, human hallucination
  labels) — e.g. a subset of RAGTruth or HaluEval, chosen for license/accessibility at build time.
- Metrics: precision/recall/F1 against human-labeled hallucination spans, plus a calibration check
  (predicted confidence vs empirical accuracy, bucketed).
- "Working" = the scorer's flagged claims meaningfully overlap with human-labeled hallucinations (F1
  clearly above a naive baseline like "always say supported"), and the confidence score is reasonably
  calibrated, not just directionally correct.

## 8. Milestones

- **M1 — Scaffold**: FastAPI project, Pydantic schemas, Docker Compose, Postgres migrations, dataset
  ingestion script
- **M2 — Core scoring loop**: claim extraction, LLM-judge entailment check, aggregation into a single
  score + flagged claims
- **M3 — Benchmark harness**: run against the public dataset, compute precision/recall/F1 + calibration,
  generate a report
- **M4 — Report viewer**: React app showing per-example scoring results and aggregate benchmark metrics
- **M5 — Polish**: README with real benchmark numbers, tests, docs, tagged release

## 9. Best Practices Checklist

- [x] Unit tests for claim extraction parsing and aggregation logic
- [x] Integration test for the full answer+sources → score path (mocked LLM-judge calls)
- [x] Typed request/response schemas (Pydantic) shared between API and benchmark CLI
- [x] Structured logging of scoring runs (no ad hoc prints)
- [x] CI pipeline: lint + type-check + tests on push
- [x] Dockerized for one-command local run
- [x] README documents real benchmark numbers (precision/recall/F1, calibration) once M3 lands
- [ ] Dataset license/usage terms checked and documented before redistribution of any sample data
