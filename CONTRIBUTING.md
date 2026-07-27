# Contributing

This started as a solo portfolio project, but issues and PRs are welcome.

## Setup

```bash
cp .env.example .env
# edit .env and set SCORER_MISTRAL_API_KEY to a real key from https://console.mistral.ai
pip install -e ".[dev]"
docker compose up -d --build
```

Frontend (optional, only needed if you're touching `web/`):

```bash
cd web
npm install
npm run dev
```

## Before opening a PR

```bash
ruff check .
mypy src
pytest -v
```

All three must pass — CI runs the same checks on every push and PR. If you're touching `web/`, also run:

```bash
cd web && npx tsc -b && npm run lint
```

## Guidelines

- Keep changes scoped — a bug fix shouldn't carry an unrelated refactor.
- Add or update tests for behavior changes. See `PLANNING.md` for the project's evaluation/benchmark
  philosophy — this project cares about real, honestly-reported numbers over green checkmarks.
- No fabricated or placeholder benchmark data. If a change affects scoring behavior, note whether the
  benchmark numbers in `README.md` need re-running.
- Match the existing code style (no comments explaining *what* code does; comments only for non-obvious
  *why*).

## Reporting bugs / requesting features

Use the GitHub issue templates. For anything security-related, see [SECURITY.md](./SECURITY.md) instead of
opening a public issue.
