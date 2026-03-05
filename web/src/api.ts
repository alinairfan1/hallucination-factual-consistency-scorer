import type { BenchmarkExample, BenchmarkSummary, LiveScoringRun } from "./types";
import { benchmarkExamples, benchmarkSummary, liveScoringRuns } from "./mockData";

/**
 * Shaped to match the read endpoints the backend still needs to build (see PRODUCT.md /
 * DESIGN.md surface brief): GET /v1/benchmark and GET /v1/scoring-runs. Swap this module's
 * export for a `fetch`-backed implementation once those exist — every component below only
 * depends on this interface, never on `mockData` directly.
 */
export interface ReportViewerApi {
  getBenchmarkSummary(): Promise<BenchmarkSummary>;
  getBenchmarkExamples(): Promise<BenchmarkExample[]>;
  getLiveScoringRuns(): Promise<LiveScoringRun[]>;
}

const SIMULATED_LATENCY_MS = 400;

function delay<T>(value: T): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), SIMULATED_LATENCY_MS));
}

export const mockApi: ReportViewerApi = {
  getBenchmarkSummary: () => delay(benchmarkSummary),
  getBenchmarkExamples: () => delay(benchmarkExamples),
  getLiveScoringRuns: () => delay(liveScoringRuns),
};

export const api: ReportViewerApi = mockApi;
