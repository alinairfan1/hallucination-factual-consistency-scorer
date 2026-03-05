import { useEffect, useState } from "react";
import type { BenchmarkExample, BenchmarkSummary, LiveScoringRun } from "./types";
import { api } from "./api";
import { StatStrip } from "./components/StatStrip";
import { BenchmarkSection } from "./components/BenchmarkSection";
import { LiveHistorySection } from "./components/LiveHistorySection";
import { ErrorPanel } from "./components/StatusPanels";
import styles from "./App.module.css";

function App() {
  const [summary, setSummary] = useState<BenchmarkSummary | null>(null);
  const [examples, setExamples] = useState<BenchmarkExample[] | null>(null);
  const [liveRuns, setLiveRuns] = useState<LiveScoringRun[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    Promise.all([api.getBenchmarkSummary(), api.getBenchmarkExamples(), api.getLiveScoringRuns()])
      .then(([summaryResult, examplesResult, liveRunsResult]) => {
        if (cancelled) return;
        setSummary(summaryResult);
        setExamples(examplesResult);
        setLiveRuns(liveRunsResult);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Failed to load scorer report data.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <span className={styles.kicker}>Hallucination / Factual-Consistency Scorer</span>
        <h1 className={styles.title}>Scorer Report</h1>
        <p className={styles.subtitle}>
          Real, claim-level results — every aggregate number below traces to a visible verdict and a
          judge-written reason, not a single opaque pass/fail score.
        </p>
      </header>

      {error && <ErrorPanel message={error} />}

      {!error && summary && <StatStrip summary={summary} />}

      {!error && (
        <BenchmarkSection summary={summary} examples={examples} loading={loading} />
      )}

      {!error && <LiveHistorySection runs={liveRuns} loading={loading} />}

      <footer className={styles.footer}>
        Read-only report — scoring is triggered via the API, not from this page.
      </footer>
    </main>
  );
}

export default App;
