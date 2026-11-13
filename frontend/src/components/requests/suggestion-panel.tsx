"use client";

import { useState } from "react";
import { Check, PencilLine, RefreshCw, Sparkles, X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Label, Select } from "@/components/ui/input";
import { DECISION_LABELS, PRIORITIES, PRIORITY_LABELS, formatDateTime } from "@/lib/labels";
import type { Priority, ReferenceData, RequestDetail, Suggestion } from "@/lib/types";
import { ConfidenceBar } from "./badges";

type Act = (path: string, body?: unknown) => Promise<void>;

/** Proposition de l'IA : l'agent accepte, corrige ou rejette. Rien n'est appliqué sans lui (BR-05). */
export function SuggestionPanel({ req, refData, act }: { req: RequestDetail; refData: ReferenceData; act: Act }) {
  const s = req.suggestion;
  const [mode, setMode] = useState<"view" | "modify">("view");
  if (!s) return null;
  const isMock = s.provider.startsWith("mock");
  const category = refData.categories.find((c) => c.id === s.proposal.category_id);
  const team = refData.teams.find((t) => t.id === s.proposal.team_id);
  const pending = s.decision === "PENDING" && req.status === "NEW";

  if (!pending) return <DecisionSummary s={s} refData={refData} canRetry={req.status === "NEW" && req.can_edit} act={act} reqId={req.id} />;

  const decide = (body: Record<string, unknown>) => act(`/api/suggestions/${s.id}/decision`, body);

  return (
    <Card className="border-navy-200">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line bg-navy-50/60 px-5 py-3">
        <h2 className="flex items-center gap-2 font-semibold text-navy-800">
          <Sparkles className="size-4" aria-hidden /> Proposition de tri
        </h2>
        <span className="text-xs text-muted">
          {isMock ? "Mode démonstration (règles)" : s.provider} · {s.latency_ms} ms
        </span>
      </div>

      {mode === "view" ? (
        <dl className="grid gap-x-6 gap-y-3 px-5 py-4 sm:grid-cols-3">
          <Proposed label="Catégorie" value={category?.name ?? s.proposal.category_code} confidence={s.proposal.field_confidence.category} />
          <Proposed label="Priorité" value={PRIORITY_LABELS[s.proposal.priority]} confidence={s.proposal.field_confidence.priority} />
          <Proposed label="Équipe" value={team?.name ?? s.proposal.team_code} confidence={s.proposal.field_confidence.team} />
        </dl>
      ) : (
        <ModifyForm s={s} refData={refData} onCancel={() => setMode("view")} onSubmit={(v) => decide({ action: "modify", ...v })} />
      )}

      <p className="border-t border-line px-5 py-3 text-muted">
        <span className="font-medium text-ink">Pourquoi : </span>
        {s.explanation}
      </p>

      {req.can_edit && mode === "view" && (
        <div className="flex flex-wrap gap-2 border-t border-line px-5 py-3">
          <Button onClick={() => decide({ action: "accept" })}>
            <Check className="size-4" aria-hidden /> Accepter
          </Button>
          <Button variant="secondary" onClick={() => setMode("modify")}>
            <PencilLine className="size-4" aria-hidden /> Corriger
          </Button>
          <Button variant="ghost" onClick={() => decide({ action: "reject" })}>
            <X className="size-4" aria-hidden /> Rejeter et classer moi-même
          </Button>
        </div>
      )}
    </Card>
  );
}

function Proposed({ label, value, confidence }: { label: string; value: string; confidence: number }) {
  return (
    <div>
      <dt className="text-xs text-muted">{label}</dt>
      <dd className="mt-0.5 font-medium">{value}</dd>
      <dd className="mt-1">
        <ConfidenceBar value={confidence} />
      </dd>
    </div>
  );
}

function ModifyForm({
  s,
  refData,
  onCancel,
  onSubmit,
}: {
  s: Suggestion;
  refData: ReferenceData;
  onCancel: () => void;
  onSubmit: (v: { category_id: string; priority: Priority; team_id: string }) => void;
}) {
  const [category, setCategory] = useState(s.proposal.category_id);
  const [priority, setPriority] = useState<Priority>(s.proposal.priority);
  const [team, setTeam] = useState(s.proposal.team_id);
  return (
    <div className="space-y-3 px-5 py-4">
      <div className="grid gap-3 sm:grid-cols-3">
        <div>
          <Label htmlFor="m-cat">Catégorie</Label>
          <Select
            id="m-cat"
            value={category}
            onChange={(e) => {
              setCategory(e.target.value);
              const def = refData.categories.find((c) => c.id === e.target.value)?.default_team_id;
              if (def) setTeam(def);
            }}
          >
            {refData.categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </Select>
        </div>
        <div>
          <Label htmlFor="m-prio">Priorité</Label>
          <Select id="m-prio" value={priority} onChange={(e) => setPriority(e.target.value as Priority)}>
            {PRIORITIES.map((p) => (
              <option key={p} value={p}>
                {PRIORITY_LABELS[p]}
              </option>
            ))}
          </Select>
        </div>
        <div>
          <Label htmlFor="m-team">Équipe</Label>
          <Select id="m-team" value={team} onChange={(e) => setTeam(e.target.value)}>
            {refData.teams.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </Select>
        </div>
      </div>
      <div className="flex gap-2">
        <Button onClick={() => onSubmit({ category_id: category, priority, team_id: team })}>Appliquer ma correction</Button>
        <Button variant="ghost" onClick={onCancel}>
          Annuler
        </Button>
      </div>
    </div>
  );
}

function DecisionSummary({
  s,
  refData,
  canRetry,
  act,
  reqId,
}: {
  s: Suggestion;
  refData: ReferenceData;
  canRetry: boolean;
  act: Act;
  reqId: string;
}) {
  const tone = s.decision === "ACCEPTED" ? "success" : s.decision === "MODIFIED" ? "warning" : s.decision === "REJECTED" ? "danger" : "neutral";
  const name = (id: string | undefined) => refData.categories.find((c) => c.id === id)?.name;
  const changed: string[] = [];
  if (s.final_value && s.decision === "MODIFIED") {
    if (s.final_value.category_id !== s.proposal.category_id) changed.push(`catégorie → ${name(s.final_value.category_id)}`);
    if (s.final_value.priority !== s.proposal.priority) changed.push(`priorité → ${PRIORITY_LABELS[s.final_value.priority as Priority]}`);
    if (s.final_value.team_id !== s.proposal.team_id)
      changed.push(`équipe → ${refData.teams.find((t) => t.id === s.final_value?.team_id)?.name}`);
  }
  return (
    <Card className="flex flex-wrap items-center gap-x-3 gap-y-2 px-5 py-3">
      <Sparkles className="size-4 text-navy-700" aria-hidden />
      <span className="font-medium">Proposition de tri</span>
      <Badge tone={tone}>{DECISION_LABELS[s.decision]}</Badge>
      <span className="text-muted">
        {name(s.proposal.category_id)} · {PRIORITY_LABELS[s.proposal.priority]}
        {changed.length > 0 && <> — corrigée : {changed.join(", ")}</>}
        {s.decided_by && (
          <>
            {" "}
            · {s.decided_by.full_name}, {formatDateTime(s.decided_at)}
          </>
        )}
      </span>
      {canRetry && s.decision === "REJECTED" && (
        <Button variant="ghost" className="ml-auto" onClick={() => act(`/api/requests/${reqId}/suggestion`)}>
          <RefreshCw className="size-4" aria-hidden /> Nouvelle proposition
        </Button>
      )}
    </Card>
  );
}
