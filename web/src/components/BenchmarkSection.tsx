import type { BenchmarkExample, BenchmarkSummary } from "../types";
import { SectionPanel } from "./SectionPanel";
import { ExampleRow } from "./ExampleRow";
import { CalibrationTable } from "./CalibrationTable";
import { RowSkeletons } from "./StatusPanels";
import styles from "./BenchmarkSection.module.css";

interface BenchmarkSectionProps {
  summary: BenchmarkSummary | null;
  examples: BenchmarkExample[] | null;
  loading: boolean;
}

export function BenchmarkSection({ summary, examples, loading }: BenchmarkSectionProps) {
  return (
    <SectionPanel
      title="Benchmark Results"
      meta={summary ? `${summary.datasetName} · judged by ${summary.judgeModel}` : undefined}
    >
      <div className={styles.layout}>
        {summary && (
          <div className={styles.limitations}>
            <div className={styles.limitationsTitle}>Known limitations</div>
            <ul className={styles.limitationsList}>
              {summary.knownLimitations.map((limitation, index) => (
                <li key={index}>{limitation}</li>
              ))}
            </ul>
          </div>
        )}

        <div>
          <p className={styles.subhead}>
            Calibration — does a higher score actually mean more likely supported?
          </p>
          {summary ? <CalibrationTable buckets={summary.calibration} /> : <RowSkeletons count={2} />}
        </div>

        <div>
          <p className={styles.subhead}>
            {examples ? `${examples.length} representative example${examples.length === 1 ? "" : "s"} — expand any row for the judge's claim-level reasoning` : "Loading examples…"}
          </p>
          {loading || !examples ? (
            <RowSkeletons count={6} />
          ) : (
            <div>
              {examples.map((example) => (
                <ExampleRow
                  key={example.id}
                  id={example.id}
                  question={example.question}
                  answer={example.answer}
                  sources={example.sources}
                  score={example.score}
                  rightBadge={example.humanLabel}
                  claims={example.claims}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </SectionPanel>
  );
}
