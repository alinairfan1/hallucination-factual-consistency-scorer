import type { Verdict } from "../types";
import styles from "./VerdictTag.module.css";

const LABELS: Record<Verdict, string> = {
  entailed: "Entailed",
  contradicted: "Contradicted",
  not_enough_info: "Not enough info",
};

export function VerdictTag({ verdict }: { verdict: Verdict }) {
  return <span className={`${styles.tag} ${styles[verdict]}`}>{LABELS[verdict]}</span>;
}
