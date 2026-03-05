import type { LiveScoringRun } from "../types";
import { SectionPanel } from "./SectionPanel";
import { ExampleRow } from "./ExampleRow";
import { EmptyState, RowSkeletons } from "./StatusPanels";

interface LiveHistorySectionProps {
  runs: LiveScoringRun[] | null;
  loading: boolean;
}

function formatTimestamp(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export function LiveHistorySection({ runs, loading }: LiveHistorySectionProps) {
  return (
    <SectionPanel title="Live Scoring History" meta="POST /v1/score call log">
      {loading || !runs ? (
        <RowSkeletons count={3} />
      ) : runs.length === 0 ? (
        <EmptyState>
          No live scoring calls yet — run <code className="mono">POST /v1/score</code> against the API to
          populate this section.
        </EmptyState>
      ) : (
        <div>
          {runs.map((run) => (
            <ExampleRow
              key={run.id}
              id={run.id}
              question="Live /v1/score call"
              answer={run.answer}
              sources={run.sources}
              score={run.score}
              rightBadge={formatTimestamp(run.timestamp)}
              claims={run.claims}
            />
          ))}
        </div>
      )}
    </SectionPanel>
  );
}
