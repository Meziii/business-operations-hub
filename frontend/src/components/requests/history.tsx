import { FIELD_LABELS, PRIORITY_LABELS, STATUS_LABELS, DECISION_LABELS, formatDateTime } from "@/lib/labels";
import type { Decision, Priority, RequestEvent, Status } from "@/lib/types";

function value(field: string | null, v: string | null): string {
  if (v === null) return "—";
  if (field === "status") return STATUS_LABELS[v as Status] ?? v;
  if (field === "priority") return PRIORITY_LABELS[v as Priority] ?? v;
  return v;
}

function describe(e: RequestEvent): React.ReactNode {
  switch (e.event_type) {
    case "created":
      return "a créé la demande";
    case "ai_suggested":
      return <>Proposition de tri générée ({e.new_value})</>;
    case "ai_decision":
      return <>a traité la proposition : {DECISION_LABELS[e.new_value as Decision]?.toLowerCase() ?? e.new_value}</>;
    case "status_changed":
      return (
        <>
          a changé le statut : {value("status", e.old_value)} → <strong className="font-medium">{value("status", e.new_value)}</strong>
        </>
      );
    case "field_changed":
      return (
        <>
          a modifié {FIELD_LABELS[e.field ?? ""]?.toLowerCase() ?? e.field} : {value(e.field, e.old_value)} →{" "}
          <strong className="font-medium">{value(e.field, e.new_value)}</strong>
        </>
      );
    case "comment_added":
      return "a ajouté un commentaire";
    case "attachment_added":
      return <>a joint « {e.new_value} »</>;
    default:
      return e.event_type;
  }
}

/** Historique complet : qui, quoi, quand, avant / après (BR-04). */
export function History({ events }: { events: RequestEvent[] }) {
  return (
    <ol className="space-y-3 px-5 py-4">
      {[...events].reverse().map((e) => (
        <li key={e.id} className="flex gap-3">
          <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-navy-200" aria-hidden />
          <div>
            <p>
              {e.event_type !== "ai_suggested" && <span className="font-medium">{e.actor?.full_name ?? "Système"} </span>}
              {describe(e)}
            </p>
            <p className="text-xs text-muted">{formatDateTime(e.created_at)}</p>
          </div>
        </li>
      ))}
    </ol>
  );
}
