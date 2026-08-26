type StatusBadgeProps = {
  status: string;
};

const labels: Record<string, string> = {
  draft: "Rascunho",
  active: "Ativa",
  corrected: "Corrigida",
  archived: "Arquivada",
};

export function StatusBadge({ status }: StatusBadgeProps) {
  return <span className={`status-badge ${status}`}>{labels[status] ?? status}</span>;
}
