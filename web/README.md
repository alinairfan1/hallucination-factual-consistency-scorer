# Scorer Report Viewer

The M4 report viewer for the [Hallucination / Factual-Consistency Scorer](../README.md): a read-only,
single-page dashboard surfacing real benchmark results (precision/recall/F1, calibration) and live
`/v1/score` call history, with claim-level judge reasoning available on every row. See the project root's
[`PRODUCT.md`](../PRODUCT.md) and [`DESIGN.md`](../DESIGN.md) for the product and visual design system this
was built against.

## Status

Built against typed mock data (`src/mockData.ts`) shaped to match the backend's real, documented benchmark
numbers, since the backend does not yet persist per-example benchmark results or expose a scoring-history
read endpoint (see `PRODUCT.md`'s "Explicitly undecided" section). Swap `src/api.ts`'s `mockApi` export for
a `fetch`-backed implementation of the same `ReportViewerApi` interface once those backend endpoints exist
— no component depends on `mockData` directly.

## Develop

```bash
npm install
npm run dev
```

## Build / lint / typecheck

```bash
npm run build
npm run lint
npx tsc -b --noEmit
```
