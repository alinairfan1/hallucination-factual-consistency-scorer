import styles from "./StatusPanels.module.css";

export function EmptyState({ children }: { children: React.ReactNode }) {
  return <p className={styles.empty}>{children}</p>;
}

export function ErrorPanel({ message }: { message: string }) {
  return (
    <div className={styles.error}>
      <span className={styles.errorLabel}>Error</span>
      {message}
    </div>
  );
}

export function RowSkeletons({ count = 4 }: { count?: number }) {
  return (
    <div>
      {Array.from({ length: count }).map((_, index) => (
        <div key={index} className={styles.skeletonRow} />
      ))}
    </div>
  );
}
