# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Two audiences, portfolio-first:

- **Portfolio reviewers** (recruiters, technical interviewers) skimming to quickly judge whether the
  scorer actually works and is well-engineered. This is the primary audience — the surface needs to read
  as competent, real engineering within the first few seconds.
- **The builder / a future operator**, inspecting real benchmark and live-scoring results in depth —
  debugging why a specific claim got flagged, checking calibration, spot-checking judge reasoning.

Both audiences look at the same read-only data; the portfolio audience just needs the first impression to
land immediately, while the operator audience needs real drill-down depth to be genuinely there, not just
implied.

## Product Purpose

The underlying product (see `PLANNING.md`, `README.md`) is a hallucination / factual-consistency scorer:
given an LLM's answer and its source documents, it decomposes the answer into atomic claims, checks each
claim's entailment against the sources via an LLM judge (Mistral AI, `mistral-large-latest`), and produces
an aggregate confidence score plus a list of flagged unsupported/contradicted claims — benchmarked against
a real, licensed public dataset (HaluEval QA) rather than a synthetic demo.

The report viewer is the visual surface that makes that real, measured behavior visible and inspectable.
It does not add new scoring capability — it displays what the backend has already computed. Success means
a visitor can, within seconds, see the scorer works and roughly how well (with the real, honestly-caveated
numbers already written into `README.md`), and can drill into any individual example to see exactly which
claims were flagged and why.

## Positioning

Most "does this answer hallucinate" demos show a single pass/fail number with no visibility into how it
was reached, and are rarely benchmarked against anything real. This project's differentiator — and what
the viewer exists to make visible, not just claim — is: (1) claim-level decomposition with a visible
verdict + reason per claim, not one opaque whole-answer judgment, and (2) real measured numbers against a
licensed public benchmark, reported with their actual caveats (a documented naive-baseline ceiling,
imperfect calibration, honest residual failure cases) rather than a cherry-picked headline metric.

## Operating Context

- Backend: FastAPI + Postgres (via Docker Compose), judge calls via Mistral AI.
- Benchmark runs are triggered via a CLI (`scorer-benchmark`) against the committed 100-example HaluEval QA
  subset (`data/halueval_qa_benchmark.jsonl`); it currently prints an aggregate report to stdout.
- Live scoring happens via `POST /v1/score`, which logs each request's summary stats (answer, source
  count, score, flagged-claim count, timestamp) to a `scoring_runs` Postgres table.
- The viewer is a separate React + TypeScript app (stack already committed in this project's own docs)
  reading from this backend; it does not replace or modify the scoring pipeline itself.

## Capabilities and Constraints

Confirmed:
- Read-only in this iteration — no interactive "paste an answer, get a live score" form. The surface tells
  the story of what already happened, not a live demo you type into.
- Two sections of data: (1) benchmark run results — per-example claims/verdicts/reasons plus aggregate
  precision/recall/F1 and the calibration breakdown; (2) live `/v1/score` call history.

Explicitly undecided / real implementation dependencies the build phase must resolve, not invented here:
- Today, `scorer-benchmark` only prints an aggregate report to stdout — no per-example benchmark result is
  persisted anywhere. The viewer's benchmark section needs that data persisted somewhere first (e.g. a
  structured output file or a DB table), which is new backend work, not just frontend.
- The `scoring_runs` table currently stores only summary fields (score, source count, flagged-claim count,
  timestamp) — it does not store the sources, the individual flagged claims, or their reasons, and there
  is no read endpoint for it yet. Full claim-level drill-down for live history requires both a schema
  change and a new `GET` endpoint.

## Evidence on Hand

- Real dataset: `data/halueval_qa_benchmark.jsonl`, 100 examples from HaluEval (MIT-licensed, provenance
  documented in `data/README.md`).
- Real, already-published benchmark numbers in `README.md`: Precision 87.0%, Recall 80.0%, F1 83.3% vs. a
  documented ~73.7% naive-length-heuristic ceiling, plus a full calibration table (score → empirical
  supported rate). These are the real numbers to surface — never fabricate different ones, and preserve
  the honest caveats (small sample size, imperfect calibration, one known unfixed failure case, likely
  dataset label noise on at least one row) rather than smoothing them away.
- No screenshots, mockups, testimonials, case studies, or pricing exist. None should be invented.

## Product Principles

1. Real numbers, honestly caveated — never a vibe metric, and never hide an unfavorable qualifier the
   project's own docs already state plainly.
2. Make reasoning inspectable, not just verdicts — every flagged claim shows its judge-written reason, not
   only entailed/contradicted/not_enough_info.
3. Portfolio-credible first, operationally real second — every screen must read as competent engineering
   to a skimming reviewer, while still holding up to an operator's real drill-down.
4. Read-only — this surface reports what happened; it does not become a second way to trigger scoring.
