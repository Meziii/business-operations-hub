import { AlertTriangle, CheckCircle2, Clock } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { PRIORITY_LABELS, SLA_LABELS, STATUS_LABELS, formatRelative } from "@/lib/labels";
import type { Priority, SlaState, Status } from "@/lib/types";
import { cn } from "@/lib/utils";

const STATUS_TONE: Record<Status, "neutral" | "navy" | "success" | "warning" | "danger"> = {
  NEW: "warning",
  CLASSIFIED: "neutral",
  ASSIGNED: "navy",
  IN_PROGRESS: "navy",
  WAITING_INFO: "warning",
  RESOLVED: "success",
  CLOSED: "neutral",
};

export function StatusBadge({ status }: { status: Status }) {
  return <Badge tone={STATUS_TONE[status]}>{STATUS_LABELS[status]}</Badge>;
}

const PRIORITY_DOT: Record<Priority, string> = {
  LOW: "bg-muted/40",
  MEDIUM: "bg-navy-600",
  HIGH: "bg-warning",
  CRITICAL: "bg-danger",
};

export function PriorityLabel({ priority }: { priority: Priority | null }) {
  if (!priority) return <span className="text-muted">—</span>;
  return (
    <span className="inline-flex items-center gap-1.5 whitespace-nowrap">
      <span className={cn("size-2 rounded-full", PRIORITY_DOT[priority])} aria-hidden />
      {PRIORITY_LABELS[priority]}
    </span>
  );
}

/** État SLA : texte + icône, jamais la couleur seule. */
export function SlaIndicator({ state, due, compact = false }: { state: SlaState; due: string | null; compact?: boolean }) {
  if (state === "NONE") return <span className="text-muted">—</span>;
  const Icon = state === "BREACHED" ? AlertTriangle : state === "MET" ? CheckCircle2 : Clock;
  const color =
    state === "BREACHED" ? "text-danger" : state === "AT_RISK" ? "text-warning" : state === "MET" ? "text-success" : "text-muted";
  // Un retard peut venir de la prise en charge alors que la résolution est encore à venir :
  // dans ce cas, afficher l'échéance future (« dans 12 heures ») contredirait l'icône rouge.
  const duePassed = due !== null && new Date(due).getTime() < Date.now();
  const text =
    state === "MET"
      ? "Respecté"
      : state === "BREACHED"
        ? due && duePassed
          ? formatRelative(due)
          : SLA_LABELS.BREACHED
        : due
          ? formatRelative(due)
          : SLA_LABELS[state];
  const prefix = !compact && text !== SLA_LABELS[state];
  return (
    <span className={cn("inline-flex items-center gap-1.5 whitespace-nowrap", color)} title={SLA_LABELS[state]}>
      <Icon className="size-3.5 shrink-0" aria-hidden />
      <span>
        {prefix ? <span className="sr-only">{SLA_LABELS[state]} : </span> : null}
        {text}
      </span>
    </span>
  );
}

export function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const tone = value >= 0.75 ? "bg-success" : value >= 0.5 ? "bg-warning" : "bg-danger";
  return (
    <span className="inline-flex items-center gap-2" title={`Confiance ${pct} %`}>
      <span className="h-1.5 w-16 overflow-hidden rounded-full bg-line" aria-hidden>
        <span className={cn("block h-full rounded-full", tone)} style={{ width: `${pct}%` }} />
      </span>
      <span className="w-9 text-xs tabular-nums text-muted">{pct} %</span>
    </span>
  );
}
