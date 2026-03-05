import type { BenchmarkExample, BenchmarkSummary, LiveScoringRun } from "./types";
import { KNOWN_LIMITATIONS, benchmarkExamples, benchmarkSummary, liveScoringRuns } from "./mockData";

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

interface BackendBenchmarkResponse extends Omit<BenchmarkSummary, "knownLimitations"> {
  examples: BenchmarkExample[];
}

function createFetchApi(baseUrl: string): ReportViewerApi {
  // GET /v1/benchmark returns summary + examples together; both report-viewer methods
  // share one in-flight request instead of fetching it twice.
  let benchmarkRequest: Promise<BackendBenchmarkResponse> | null = null;

  async function fetchBenchmark(): Promise<BackendBenchmarkResponse> {
    if (!benchmarkRequest) {
      benchmarkRequest = fetch(`${baseUrl}/v1/benchmark`).then(async (response) => {
        if (!response.ok) {
          if (response.status === 404) {
            throw new Error("No benchmark run has been persisted yet — run `scorer-benchmark`.");
          }
          throw new Error(`GET /v1/benchmark failed with ${response.status}`);
        }
        return (await response.json()) as BackendBenchmarkResponse;
      });
    }
    return benchmarkRequest;
  }

  return {
    async getBenchmarkSummary() {
      const { examples: _examples, ...summary } = await fetchBenchmark();
      return { ...summary, knownLimitations: KNOWN_LIMITATIONS };
    },
    async getBenchmarkExamples() {
      const { examples } = await fetchBenchmark();
      return examples;
    },
    async getLiveScoringRuns() {
      const response = await fetch(`${baseUrl}/v1/scoring-runs`);
      if (!response.ok) {
        throw new Error(`GET /v1/scoring-runs failed with ${response.status}`);
      }
      return (await response.json()) as LiveScoringRun[];
    },
  };
}

// Defaults to the polished, already-verified mock data (see mockData.ts) so `npm run dev`
// works with zero setup. Set VITE_API_BASE_URL (e.g. http://localhost:8000) to point this
// at a real running backend instead.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL as string | undefined;

export const api: ReportViewerApi = API_BASE_URL ? createFetchApi(API_BASE_URL) : mockApi;
