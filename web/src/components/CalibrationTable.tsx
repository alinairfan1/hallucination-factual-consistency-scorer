import type { CalibrationBucket } from "../types";
import styles from "./CalibrationTable.module.css";

export function CalibrationTable({ buckets }: { buckets: CalibrationBucket[] }) {
  return (
    <div>
      <div className={styles.wrap}>
        <div className={`${styles.row} ${styles.head}`}>
          <span>Score</span>
          <span>n</span>
          <span>Empirically supported</span>
        </div>
        {buckets.map((bucket) => (
          <div key={bucket.score} className={styles.row}>
            <span className={styles.cell}>{bucket.score.toFixed(2)}</span>
            <span className={styles.cell}>{bucket.count}</span>
            <span className={styles.cell}>
              <div className={styles.bar}>
                <div className={styles.barFill} style={{ width: `${bucket.empiricalSupportedRate}%` }} />
              </div>
              <span style={{ marginLeft: 8 }}>{bucket.empiricalSupportedRate.toFixed(1)}%</span>
            </span>
          </div>
        ))}
      </div>
      <p className={styles.note}>
        Two largest buckets shown — directional, not tightly calibrated. Full per-score breakdown is
        printed by <code className="mono">scorer-benchmark</code>.
      </p>
    </div>
  );
}
