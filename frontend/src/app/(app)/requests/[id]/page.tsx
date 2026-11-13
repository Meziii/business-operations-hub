"use client";

import { use, useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { ArrowLeft, FileText, Paperclip, Upload } from "lucide-react";
import { History } from "@/components/requests/history";
import { PriorityLabel, SlaIndicator, StatusBadge } from "@/components/requests/badges";
import { SuggestionPanel } from "@/components/requests/suggestion-panel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { ErrorMessage, Spinner } from "@/components/ui/feedback";
import { Label, Select, Textarea } from "@/components/ui/input";
import { ApiError, api } from "@/lib/api";
import {
  CHANNEL_LABELS,
  PRIORITIES,
  PRIORITY_LABELS,
  SLA_LABELS,
  TRANSITION_LABELS,
  formatDateTime,
  formatRelative,
} from "@/lib/labels";
import type { ReferenceData, RequestDetail, Status } from "@/lib/types";

const NEEDS_COMMENT: Status[] = ["WAITING_INFO", "RESOLVED"];

export default function RequestDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [req, setReq] = useState<RequestDetail | null>(null);
  const [refData, setRefData] = useState<ReferenceData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api<RequestDetail>(`/api/requests/${id}`)
      .then(setReq)
      .catch((e: Error) => (e instanceof ApiError && e.status === 404 ? setNotFound(true) : setError(e.message)));
    api<ReferenceData>("/api/reference").then(setRefData).catch((e: Error) => setError(e.message));
  }, [id]);

  /** Envoie une action et remplace la demande par la version renvoyée par l'API. */
  const act = useCallback(async (path: string, body?: unknown, method = "POST") => {
    setBusy(true);
    setError(null);
    try {
      setReq(await api<RequestDetail>(path, { method, body: body === undefined ? undefined : JSON.stringify(body) }));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }, []);

  if (notFound) return <ErrorMessage message="Demande introuvable, ou vous n'avez pas accès à cette demande." />;
  if (!req || !refData) return error ? <ErrorMessage message={error} /> : <Spinner />;

  return (
    <>
      <Link href="/requests" className="mb-3 inline-flex items-center gap-1 text-muted hover:text-ink">
        <ArrowLeft className="size-4" aria-hidden /> Demandes
      </Link>
      <div className="mb-5 flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-muted">
            {req.reference} · {req.account.name}
            {req.account_tier === "PREMIUM" && (
              <span className="ml-2">
                <Badge tone="navy">Premium</Badge>
              </span>
            )}
          </p>
          <h1 className="mt-1 text-xl font-semibold tracking-tight">{req.title}</h1>
          <div className="mt-2 flex flex-wrap items-center gap-3">
            <StatusBadge status={req.status} />
            <PriorityLabel priority={req.priority} />
            <SlaIndicator state={req.sla_state} due={req.sla_next_due} />
          </div>
        </div>
        <Transitions req={req} act={act} busy={busy} />
      </div>

      {error && (
        <div className="mb-4">
          <ErrorMessage message={error} />
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <SuggestionPanel req={req} refData={refData} act={act} />

          <Card>
            <CardHeader title="Description" description={`${CHANNEL_LABELS[req.channel]} · reçue le ${formatDateTime(req.created_at)}`} />
            <p className="whitespace-pre-line px-5 py-4 leading-relaxed">{req.description}</p>
          </Card>

          <Comments req={req} onAdded={() => act(`/api/requests/${req.id}`, undefined, "GET")} />
          <Attachments req={req} onAdded={() => act(`/api/requests/${req.id}`, undefined, "GET")} />

          <Card>
            <CardHeader title="Historique" description="Chaque modification, avec son auteur et la valeur précédente." />
            <History events={req.events} />
          </Card>
        </div>

        <div className="space-y-6">
          <Details req={req} refData={refData} act={act} busy={busy} />
          <Card>
            <CardHeader title="Délais (SLA)" description={SLA_LABELS[req.sla_state]} />
            <dl className="space-y-3 px-5 py-4">
              <Deadline label="Prise en charge" due={req.due_response_at} done={req.first_response_at} />
              <Deadline label="Résolution" due={req.due_resolution_at} done={req.resolved_at} />
              {req.closed_at && <Row label="Clôturée">{formatDateTime(req.closed_at)}</Row>}
            </dl>
          </Card>
        </div>
      </div>
    </>
  );
}

function Transitions({ req, act, busy }: { req: RequestDetail; act: (p: string, b?: unknown) => Promise<void>; busy: boolean }) {
  const [target, setTarget] = useState<Status | null>(null);
  const [comment, setComment] = useState("");
  if (!req.allowed_transitions.length) return null;
  const go = async (status: Status, text?: string) => {
    await act(`/api/requests/${req.id}/transition`, { status, comment: text || null });
    setTarget(null);
    setComment("");
  };
  if (target) {
    return (
      <Card className="w-full max-w-md space-y-2 p-3">
        <Label htmlFor="t-comment">
          {target === "RESOLVED" ? "Ce qui a été fait pour résoudre la demande" : "Informations à obtenir du client"}
        </Label>
        <Textarea id="t-comment" rows={3} value={comment} onChange={(e) => setComment(e.target.value)} autoFocus />
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={() => setTarget(null)}>
            Annuler
          </Button>
          <Button disabled={busy || !comment.trim()} onClick={() => go(target, comment)}>
            {TRANSITION_LABELS[target]}
          </Button>
        </div>
      </Card>
    );
  }
  return (
    <div className="flex flex-wrap gap-2">
      {req.allowed_transitions.map((s, i) => (
        <Button
          key={s}
          variant={i === 0 ? "primary" : "secondary"}
          disabled={busy}
          onClick={() => (NEEDS_COMMENT.includes(s) ? setTarget(s) : go(s))}
        >
          {req.status === "RESOLVED" && s === "IN_PROGRESS" ? "Rouvrir" : TRANSITION_LABELS[s]}
        </Button>
      ))}
    </div>
  );
}

function Details({
  req,
  refData,
  act,
  busy,
}: {
  req: RequestDetail;
  refData: ReferenceData;
  act: (p: string, b?: unknown, m?: string) => Promise<void>;
  busy: boolean;
}) {
  const disabled = !req.can_edit || busy;
  const patch = (body: Record<string, unknown>) => act(`/api/requests/${req.id}`, body, "PATCH");
  const members = refData.assignees.filter((a) => req.team && a.team_ids.includes(req.team.id));
  return (
    <Card>
      <CardHeader title="Classement et affectation" />
      <div className="space-y-3 px-5 py-4">
        <div>
          <Label htmlFor="d-cat">Catégorie</Label>
          <Select id="d-cat" disabled={disabled} value={req.category?.id ?? ""} onChange={(e) => patch({ category_id: e.target.value || null })}>
            <option value="">Non classée</option>
            {refData.categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </Select>
        </div>
        <div>
          <Label htmlFor="d-prio">Priorité</Label>
          <Select id="d-prio" disabled={disabled} value={req.priority ?? ""} onChange={(e) => patch({ priority: e.target.value || null })}>
            <option value="">Non définie</option>
            {PRIORITIES.map((p) => (
              <option key={p} value={p}>
                {PRIORITY_LABELS[p]}
              </option>
            ))}
          </Select>
        </div>
        <div>
          <Label htmlFor="d-team">Équipe</Label>
          <Select id="d-team" disabled={disabled} value={req.team?.id ?? ""} onChange={(e) => patch({ team_id: e.target.value || null })}>
            <option value="">Non routée</option>
            {refData.teams.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </Select>
        </div>
        <div>
          <Label htmlFor="d-assignee">Affectée à</Label>
          <Select
            id="d-assignee"
            disabled={disabled || !req.team || req.status === "NEW"}
            value={req.assignee?.id ?? ""}
            onChange={(e) => patch({ assignee_id: e.target.value || null })}
          >
            <option value="">Personne</option>
            {members.map((u) => (
              <option key={u.id} value={u.id}>
                {u.full_name}
              </option>
            ))}
          </Select>
          {req.status === "NEW" && <p className="mt-1 text-xs text-muted">Classez la demande avant de l&apos;affecter.</p>}
        </div>
        <dl className="space-y-2 border-t border-line pt-3">
          <Row label="Canal">{CHANNEL_LABELS[req.channel]}</Row>
          <Row label="Créée par">{req.created_by?.full_name ?? "—"}</Row>
          <Row label="Dernière modification">{formatDateTime(req.updated_at)}</Row>
        </dl>
      </div>
    </Card>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex justify-between gap-3">
      <dt className="text-muted">{label}</dt>
      <dd className="text-right">{children}</dd>
    </div>
  );
}

function Deadline({ label, due, done }: { label: string; due: string | null; done: string | null }) {
  if (!due) return <Row label={label}>Après classement</Row>;
  const late = done ? new Date(done) > new Date(due) : Date.now() > new Date(due).getTime();
  return (
    <div>
      <Row label={label}>
        <span className={late ? "font-medium text-danger" : undefined}>{formatDateTime(due)}</span>
      </Row>
      <p className="text-right text-xs text-muted">
        {done ? `Fait le ${formatDateTime(done)}${late ? " (hors délai)" : ""}` : late ? `Dépassée ${formatRelative(due)}` : `Échéance ${formatRelative(due)}`}
      </p>
    </div>
  );
}

function Comments({ req, onAdded }: { req: RequestDetail; onAdded: () => void }) {
  const [body, setBody] = useState("");
  const [error, setError] = useState<string | null>(null);
  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api(`/api/requests/${req.id}/comments`, { method: "POST", body: JSON.stringify({ body }) });
      setBody("");
      onAdded();
    } catch (err) {
      setError((err as Error).message);
    }
  };
  return (
    <Card>
      <CardHeader title="Échanges internes" description={`${req.comments.length} commentaire${req.comments.length > 1 ? "s" : ""}`} />
      {req.comments.length > 0 && (
        <ul className="divide-y divide-line">
          {req.comments.map((c) => (
            <li key={c.id} className="px-5 py-3">
              <p className="text-xs text-muted">
                <span className="font-medium text-ink">{c.author?.full_name ?? "—"}</span> · {formatDateTime(c.created_at)}
              </p>
              <p className="mt-1 whitespace-pre-line">{c.body}</p>
            </li>
          ))}
        </ul>
      )}
      {req.can_edit && (
        <form onSubmit={submit} className="space-y-2 border-t border-line px-5 py-3">
          {error && <ErrorMessage message={error} />}
          <Textarea aria-label="Nouveau commentaire" rows={2} placeholder="Ajouter un commentaire…" value={body} onChange={(e) => setBody(e.target.value)} />
          <div className="flex justify-end">
            <Button type="submit" variant="secondary" disabled={!body.trim()}>
              Commenter
            </Button>
          </div>
        </form>
      )}
    </Card>
  );
}

function Attachments({ req, onAdded }: { req: RequestDetail; onAdded: () => void }) {
  const input = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const upload = async (file: File) => {
    setUploading(true);
    setError(null);
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`/api/requests/${req.id}/attachments`, { method: "POST", body: form, credentials: "same-origin" });
    setUploading(false);
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      setError(typeof body.detail === "string" ? body.detail : "Envoi impossible.");
      return;
    }
    onAdded();
  };
  return (
    <Card>
      <CardHeader
        title="Pièces jointes"
        description="PDF uniquement, 10 Mo maximum."
        action={
          req.can_edit ? (
            <>
              <input
                ref={input}
                type="file"
                accept="application/pdf"
                className="hidden"
                onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])}
              />
              <Button variant="secondary" disabled={uploading} onClick={() => input.current?.click()}>
                <Upload className="size-4" aria-hidden /> {uploading ? "Envoi…" : "Joindre"}
              </Button>
            </>
          ) : undefined
        }
      />
      {error && (
        <div className="px-5 pt-3">
          <ErrorMessage message={error} />
        </div>
      )}
      {req.attachments.length === 0 ? (
        <p className="flex items-center gap-2 px-5 py-4 text-muted">
          <Paperclip className="size-4" aria-hidden /> Aucune pièce jointe.
        </p>
      ) : (
        <ul className="divide-y divide-line">
          {req.attachments.map((a) => (
            <li key={a.id} className="flex items-center gap-3 px-5 py-3">
              <FileText className="size-4 text-muted" aria-hidden />
              <a href={`/api/requests/${req.id}/attachments/${a.id}`} className="font-medium hover:underline">
                {a.filename}
              </a>
              <span className="ml-auto text-xs text-muted">
                {Math.max(1, Math.round(a.size_bytes / 1024))} Ko · {a.uploaded_by?.full_name}
              </span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
