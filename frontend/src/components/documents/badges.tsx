import { AlertTriangle, CheckCircle2, FileScan, Info, XCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { ANOMALY_LABELS, DOC_STATUS_LABELS } from "@/lib/labels";
import type { DocAnomaly, DocStatus } from "@/lib/types";

const STATUS_TONE: Record<DocStatus, "warning" | "success" | "neutral"> = {
  TO_REVIEW: "warning",
  VALIDATED: "success",
  REJECTED: "neutral",
};

export function DocStatusBadge({ status }: { status: DocStatus }) {
  return <Badge tone={STATUS_TONE[status]}>{DOC_STATUS_LABELS[status]}</Badge>;
}

/** Résumé des contrôles : rien, avertissements, ou blocages. Texte + icône, jamais la couleur seule. */
export function AnomalySummary({ blocking, warnings }: { blocking: number; warnings: number }) {
  if (blocking > 0)
    return (
      <span className="inline-flex items-center gap-1.5 whitespace-nowrap text-danger" title="Anomalies bloquantes">
        <XCircle className="size-3.5 shrink-0" aria-hidden />
        {blocking} bloquante{blocking > 1 ? "s" : ""}
      </span>
    );
  if (warnings > 0)
    return (
      <span className="inline-flex items-center gap-1.5 whitespace-nowrap text-warning" title="Points à vérifier">
        <AlertTriangle className="size-3.5 shrink-0" aria-hidden />
        {warnings} à vérifier
      </span>
    );
  return (
    <span className="inline-flex items-center gap-1.5 whitespace-nowrap text-success">
      <CheckCircle2 className="size-3.5 shrink-0" aria-hidden />
      Conforme
    </span>
  );
}

export function OcrTag() {
  return (
    <span className="inline-flex items-center gap-1 text-xs text-muted" title="Lu par OCR (document scanné)">
      <FileScan className="size-3.5" aria-hidden /> OCR
    </span>
  );
}

export function AnomalyItem({ anomaly }: { anomaly: DocAnomaly }) {
  const blocking = anomaly.severity === "BLOCKING";
  const Icon = blocking ? XCircle : AlertTriangle;
  return (
    <li className={`flex items-start gap-2 ${blocking ? "text-danger" : "text-warning"}`}>
      <Icon className="mt-0.5 size-4 shrink-0" aria-hidden />
      <span>
        <span className="font-medium">{ANOMALY_LABELS[anomaly.code] ?? anomaly.code}</span>
        {blocking ? " · bloquant" : " · à vérifier"}
        <span className="block text-muted">{anomaly.message}</span>
      </span>
    </li>
  );
}

export function ConfidenceDot({ value }: { value: number }) {
  const tone = value >= 0.75 ? "bg-success" : value >= 0.5 ? "bg-warning" : "bg-danger";
  return (
    <span className="inline-flex items-center gap-1.5" title={`Confiance ${Math.round(value * 100)} %`}>
      <span className={`size-2 rounded-full ${tone}`} aria-hidden />
      <span className="text-xs tabular-nums text-muted">{Math.round(value * 100)} %</span>
    </span>
  );
}

export function ProvenanceNote() {
  return (
    <p className="flex items-start gap-2 text-xs text-muted">
      <Info className="mt-0.5 size-3.5 shrink-0" aria-hidden />
      Proposition d&apos;une IA : chaque champ est à vérifier avant validation. Une valeur corrigée passe à 100 %
      de confiance.
    </p>
  );
}
