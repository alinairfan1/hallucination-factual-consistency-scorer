import { useState } from "react";
import type { ClaimResult } from "../types";
import { VerdictTag } from "./VerdictTag";
import styles from "./ExampleRow.module.css";

const VERDICT_VAR: Record<ClaimResult["verdict"], string> = {
  entailed: "var(--verdict-entailed)",
  contradicted: "var(--verdict-contradicted)",
  not_enough_info: "var(--verdict-not-enough-info)",
};

export interface ExampleRowProps {
  id: string;
  question: string;
  answer: string;
  sources: string[];
  score: number;
  rightBadge: string;
  claims: ClaimResult[];
  defaultOpen?: boolean;
}

export function ExampleRow({
  id,
  question,
  answer,
  sources,
  score,
  rightBadge,
  claims,
  defaultOpen = false,
}: ExampleRowProps) {
  const [open, setOpen] = useState(defaultOpen);
  const panelId = `${id}-detail`;

  return (
    <div className={styles.row}>
      <button
        type="button"
        className={styles.summary}
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((value) => !value)}
      >
        <span className={`${styles.chevron} ${open ? styles.chevronOpen : ""}`} aria-hidden="true">
          ▸
        </span>
        <span className={styles.qa}>
          <span className={styles.question}>{question}</span>
          <span className={styles.answer}>{answer}</span>
        </span>
        <span className={styles.badges}>
          <span className={styles.labelBadge}>{rightBadge}</span>
          <span className={styles.scoreBadge}>{score.toFixed(2)}</span>
        </span>
      </button>

      {open && (
        <div className={styles.detail} id={panelId} role="region">
          <div>
            <div className={styles.sourcesLabel}>Sources</div>
            {sources.map((source, index) => (
              <p key={index} className={styles.sourceText}>
                {source}
              </p>
            ))}
          </div>

          {claims.map((claim, index) => (
            <div
              key={index}
              className={styles.claim}
              style={{ "--claim-color": VERDICT_VAR[claim.verdict] } as React.CSSProperties}
            >
              <div className={styles.claimText}>{claim.claim}</div>
              <VerdictTag verdict={claim.verdict} />
              <div className={styles.reasonText}>{claim.reason}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
