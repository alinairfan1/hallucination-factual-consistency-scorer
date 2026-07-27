# Changelog

All notable changes to this project are documented here. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.0.0] — 2026-07-27

First complete release. Full pipeline end to end:

- FastAPI + Postgres backend with claim extraction, LLM-judge (Mistral `mistral-large-latest`) entailment
  checking, and aggregate scoring (`POST /v1/score`)
- Benchmark CLI (`scorer-benchmark`) against a real 100-example HaluEval QA subset, with precision/recall/F1
  and calibration reporting
- Per-example benchmark result and live-scoring claim-detail persistence (`GET /v1/benchmark`,
  `GET /v1/scoring-runs`)
- React + TypeScript report viewer (`web/`) — read-only dashboard over real persisted results, built to a
  documented design system (`DESIGN.md`)
- Docker Compose packaging, Alembic migrations, CI (ruff, mypy, pytest)

**Real measured results:** Precision 87.0% / Recall 80.0% / F1 83.3% against a documented ~73.7% naive
length-heuristic ceiling (see `README.md` for the full diagnosis narrative, including two rounds of
prompt-quality fixes and honestly-reported residual failure cases).
