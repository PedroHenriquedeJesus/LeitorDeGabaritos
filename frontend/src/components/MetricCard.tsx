import type { ReactNode } from "react";

type MetricCardProps = {
  label: string;
  value: number | string;
  detail: string;
  icon: ReactNode;
  tone?: "blue" | "green" | "amber" | "violet";
};

export function MetricCard({ label, value, detail, icon, tone = "blue" }: MetricCardProps) {
  return (
    <article className="metric-card">
      <div className={`metric-icon ${tone}`}>{icon}</div>
      <div>
        <span>{label}</span>
        <strong>{value}</strong>
        <small>{detail}</small>
      </div>
    </article>
  );
}
