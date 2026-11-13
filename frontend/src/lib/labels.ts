import type { Channel, Decision, Priority, SlaState, Status } from "./types";

export const STATUS_LABELS: Record<Status, string> = {
  NEW: "À classer",
  CLASSIFIED: "Classée",
  ASSIGNED: "Affectée",
  IN_PROGRESS: "En cours",
  WAITING_INFO: "En attente d'infos",
  RESOLVED: "Résolue",
  CLOSED: "Clôturée",
};

/** Libellé du bouton qui mène à ce statut. */
export const TRANSITION_LABELS: Partial<Record<Status, string>> = {
  IN_PROGRESS: "Prendre en charge",
  WAITING_INFO: "Demander des informations",
  RESOLVED: "Marquer comme résolue",
  CLOSED: "Clôturer",
};

export const PRIORITY_LABELS: Record<Priority, string> = {
  LOW: "Basse",
  MEDIUM: "Normale",
  HIGH: "Haute",
  CRITICAL: "Critique",
};

export const PRIORITIES: Priority[] = ["CRITICAL", "HIGH", "MEDIUM", "LOW"];
export const STATUSES: Status[] = ["NEW", "CLASSIFIED", "ASSIGNED", "IN_PROGRESS", "WAITING_INFO", "RESOLVED", "CLOSED"];

export const CHANNEL_LABELS: Record<Channel, string> = {
  EMAIL: "E-mail",
  PHONE: "Téléphone",
  PORTAL: "Portail client",
  PARTNER: "Partenaire",
};

export const SLA_LABELS: Record<SlaState, string> = {
  NONE: "Pas encore de SLA",
  ON_TRACK: "Dans les délais",
  AT_RISK: "Échéance proche",
  BREACHED: "En retard",
  MET: "SLA respecté",
};

export const DECISION_LABELS: Record<Decision, string> = {
  PENDING: "En attente de décision",
  ACCEPTED: "Acceptée",
  MODIFIED: "Corrigée",
  REJECTED: "Rejetée",
};

export const FIELD_LABELS: Record<string, string> = {
  status: "Statut",
  priority: "Priorité",
  category_id: "Catégorie",
  team_id: "Équipe",
  assignee_id: "Affectation",
  title: "Titre",
  description: "Description",
};

export const DOC_TYPE_LABELS: Record<string, string> = {
  INVOICE: "Facture",
  WARRANTY_CLAIM: "Demande de garantie",
};

export const DOC_STATUS_LABELS: Record<string, string> = {
  TO_REVIEW: "À vérifier",
  VALIDATED: "Validé",
  REJECTED: "Rejeté",
};

/** Message court et humain pour chaque code d'anomalie (le détail vient de l'API). */
export const ANOMALY_LABELS: Record<string, string> = {
  MISSING_FIELD: "Champ obligatoire manquant",
  DUPLICATE: "Doublon probable",
  INCONSISTENT_TOTAL: "Total incohérent",
  UNUSUAL_VAT_RATE: "Taux de TVA inhabituel",
  DUE_BEFORE_INVOICE: "Échéance avant la facture",
  DATE_IN_FUTURE: "Date dans le futur",
  FAILURE_BEFORE_PURCHASE: "Panne avant l'achat",
  OUT_OF_WARRANTY: "Hors garantie",
};

const dateTime = new Intl.DateTimeFormat("fr-FR", { dateStyle: "short", timeStyle: "short" });
const relative = new Intl.RelativeTimeFormat("fr-FR", { numeric: "auto" });

export function formatDateTime(iso: string | null): string {
  return iso ? dateTime.format(new Date(iso)) : "—";
}

/** « dans 3 h », « il y a 2 j » */
export function formatRelative(iso: string | null, now = Date.now()): string {
  if (!iso) return "—";
  const minutes = Math.round((new Date(iso).getTime() - now) / 60000);
  const abs = Math.abs(minutes);
  if (abs < 60) return relative.format(minutes, "minute");
  if (abs < 48 * 60) return relative.format(Math.round(minutes / 60), "hour");
  return relative.format(Math.round(minutes / 1440), "day");
}

export function formatDuration(minutes: number): string {
  if (minutes < 60) return `${minutes} min`;
  if (minutes < 48 * 60) return `${Math.round(minutes / 60)} h`;
  return `${Math.round(minutes / 1440)} j`;
}

export function formatPercent(x: number): string {
  return `${Math.round(x * 100)} %`;
}
