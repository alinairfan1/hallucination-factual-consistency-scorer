import type { ReactNode } from "react";
import styles from "./SectionPanel.module.css";

export function SectionPanel({
  title,
  meta,
  children,
}: {
  title: string;
  meta?: string;
  children: ReactNode;
}) {
  return (
    <section className={styles.panel}>
      <div className={styles.header}>
        <h2 className={styles.title}>{title}</h2>
        {meta && <span className={styles.meta}>{meta}</span>}
      </div>
      {children}
    </section>
  );
}
