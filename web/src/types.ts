export type Verdict = "entailed" | "contradicted" | "not_enough_info";

export interface ClaimResult {
  claim: string;
  verdict: Verdict;
  reason: string;
}

export interface BenchmarkExample {
  id: string;
  question: string;
  answer: string;
  sources: string[];
  humanLabel: "supported" | "hallucinated";
  score: number;
  claims: ClaimResult[];
}

export interface CalibrationBucket {
  score: number;
  count: number;
  empiricalSupportedRate: number;
}

export interface BenchmarkSummary {
  precision: number;
  recall: number;
  f1: number;
  /** Trivial "always supported" baseline — 0% F1 by construction, since every real run includes hallucinated examples. */
  naiveAlwaysSupportedF1: number;
  /** Best achievable F1 from a single answer-length threshold classifier — the real ceiling a judge must clear. */
  naiveLengthHeuristicF1: number;
  exampleCount: number;
  judgeModel: string;
  datasetName: string;
  calibration: CalibrationBucket[];
  knownLimitations: string[];
}

export interface LiveScoringRun {
  id: string;
  timestamp: string;
  answer: string;
  sources: string[];
  score: number;
  claims: ClaimResult[];
}
