import type { BenchmarkSummary } from "../types";
import styles from "./StatStrip.module.css";

export function StatStrip({ summary }: { summary: BenchmarkSummary }) {
  const marginValue = summary.f1 - summary.naiveLengthHeuristicF1;
  const marginLabel = `${marginValue >= 0 ? "+" : ""}${marginValue.toFixed(1)} pts margin`;

  return (
    <div className={styles.strip}>
      <div className={styles.card}>
        <span className={styles.label}>Precision</span>
        <span className={styles.value}>{summary.precision.toFixed(1)}%</span>
      </div>
      <div className={styles.card}>
        <span className={styles.label}>Recall</span>
        <span className={styles.value}>{summary.recall.toFixed(1)}%</span>
      </div>
      <div className={styles.card}>
        <span className={styles.label}>F1</span>
        <span className={styles.value}>{summary.f1.toFixed(1)}%</span>
      </div>
      <div className={styles.marginCard}>
        <span className={styles.label}>Vs. naive length-heuristic ceiling</span>
        <span className={styles.marginTop}>{summary.f1.toFixed(1)}%</span>
        <div className={styles.marginRule} />
        <span className={styles.marginBottom}>{summary.naiveLengthHeuristicF1.toFixed(1)}%</span>
        <span className={marginValue >= 0 ? styles.marginDeltaPositive : styles.marginDeltaNegative}>
          {marginLabel}
        </span>
      </div>
    </div>
  );
}
