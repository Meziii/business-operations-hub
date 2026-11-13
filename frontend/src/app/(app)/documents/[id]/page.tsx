"use client";

import { use, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, CheckCircle2, FileText, Link2, RotateCcw } from "lucide-react";
import { AnomalyItem, ConfidenceDot, DocStatusBadge, OcrTag, ProvenanceNote } from "@/components/documents/badges";
import { useSession } from "@/components/layout/session";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { ErrorMessage, Spinner } from "@/components/ui/feedback";
import { Input, Label, Select, Textarea } from "@/components/ui/input";
import { ApiError, api } from "@/lib/api";
import { DOC_TYPE_LABELS, formatDateTime } from "@/lib/labels";
import type { DocumentDetail, ExtractedField, RequestRow } from "@/lib/types";

export default function DocumentDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const me = useSession();
  const [doc, setDoc] = useState<DocumentDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [busy, setBusy] = useState(false);
  const [draft, setDraft] = useState<Record<string, string>>({});

  const load = useCallback(() => {
    api<DocumentDetail>(`/api/documents/${id}`)
      .then((d) => { setDoc(d); setDraft({}); })
      .catch((e: Error) => (e instanceof ApiError && e.status === 404 ? setNotFound(true) : setError(e.message)));
  }, [id]);

  useEffect(load, [load]);

  const act = useCallback(
    async (path: string, body?: unknown, method = "POST") => {
      setBusy(true);
      setError(null);
      try {
        const updated = await api<DocumentDetail>(path, { method, body: body === undefined ? undefined : JSON.stringify(body) });
        setDoc(updated);
        setDraft({});
      } catch (e) {
        setError((e as Error).message);
      } finally {
        setBusy(false);
      }
    },
    [],
  );

  if (notFound) return <ErrorMessage message="Document introuvable, ou vous n'avez pas accès à ce document." />;
  if (!doc) return error ? <ErrorMessage message={error} /> : <Spinner />;

  const dirty = Object.keys(draft).length > 0;
  const hasBlocking = doc.anomalies.some((a) => a.severity === "BLOCKING");

  const saveCorrections = () => {
    const data: Record<string, string | number | null> = {};
    for (const [name, raw] of Object.entries(draft)) {
      const field = doc.fields.find((f) => f.name === name);
      const trimmed = raw.trim();
      data[name] = trimmed === "" ? null : field?.kind === "amount" ? Number(trimmed.replace(",", ".")) : trimmed;
    }
    void act(`/api/documents/${doc.id}/fields`, { data }, "PATCH");
  };

  return (
    <>
      <Link href="/documents" className="mb-3 inline-flex items-center gap-1 text-muted hover:text-ink">
        <ArrowLeft className="size-4" aria-hidden /> Documents
      </Link>
      <div className="mb-5 flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="flex flex-wrap items-center gap-2 text-muted">
            {doc.reference} · {DOC_TYPE_LABELS[doc.doc_type]}
            {doc.ocr_used && <OcrTag />}
          </p>
          <h1 className="mt-1 truncate text-xl font-semibold tracking-tight">{doc.summary}</h1>
          <div className="mt-2 flex flex-wrap items-center gap-3">
            <DocStatusBadge status={doc.status} />
            {doc.decided_by && (
              <span className="text-muted">
                {doc.status === "VALIDATED" ? "Validé" : "Rejeté"} par {doc.decided_by.full_name}, {formatDateTime(doc.decided_at)}
              </span>
            )}
          </div>
        </div>
        {doc.can_edit && <Actions doc={doc} dirty={dirty} busy={busy} onValidate={() => act(`/api/documents/${doc.id}/validate`)} onReject={(reason) => act(`/api/documents/${doc.id}/reject`, { reason })} hasBlocking={hasBlocking} />}
      </div>

      {error && <div className="mb-4"><ErrorMessage message={error} /></div>}
      {doc.text_error && (
        <div className="mb-4 rounded-md border border-warning/20 bg-warning-soft px-3 py-2.5 text-warning">
          Texte illisible ({doc.text_error}) : saisissez les champs à la main en vous appuyant sur l&apos;aperçu.
        </div>
      )}
      {doc.rejection_reason && (
        <div className="mb-4 rounded-md border border-line bg-canvas px-3 py-2.5 text-muted">
          Motif du rejet : {doc.rejection_reason}
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="space-y-6">
          <Card className="overflow-hidden">
            <CardHeader title="Aperçu" description={`${doc.page_count} page${doc.page_count > 1 ? "s" : ""} · ${(doc.size_bytes / 1024).toFixed(0)} Ko${doc.ocr_confidence != null ? ` · OCR ${Math.round(doc.ocr_confidence * 100)} %` : ""}`} />
            <iframe src={`/api/documents/${doc.id}/file`} title={`Aperçu de ${doc.reference}`} className="h-[600px] w-full border-0 bg-canvas" />
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader title="Champs extraits" description={`Proposés par ${doc.provider}.`} />
            <div className="space-y-3 px-5 py-4">
              <ProvenanceNote />
              {doc.fields.map((f) => (
                <FieldRow
                  key={f.name}
                  field={f}
                  editable={doc.can_edit}
                  draft={draft[f.name]}
                  onChange={(v) => setDraft((d) => ({ ...d, [f.name]: v }))}
                />
              ))}
              {doc.can_edit && dirty && (
                <div className="flex justify-end gap-2 border-t border-line pt-3">
                  <Button variant="ghost" disabled={busy} onClick={() => setDraft({})}>Annuler</Button>
                  <Button disabled={busy} onClick={saveCorrections}>Enregistrer les corrections</Button>
                </div>
              )}
            </div>
          </Card>

          <Card>
            <CardHeader title="Contrôles" description="Vérifiés à chaque correction." />
            <div className="px-5 py-4">
              {doc.anomalies.length === 0 ? (
                <p className="flex items-center gap-2 text-success"><CheckCircle2 className="size-4" aria-hidden /> Aucune anomalie détectée.</p>
              ) : (
                <ul className="space-y-2.5">{doc.anomalies.map((a, i) => <AnomalyItem key={i} anomaly={a} />)}</ul>
              )}
            </div>
          </Card>

          <LinkCard doc={doc} editable={doc.status !== "REJECTED" && me.role !== "VIEWER"} busy={busy} onLink={(rid) => act(`/api/documents/${doc.id}/request`, { request_id: rid }, "PUT")} />

          {doc.versions.length > 1 && (
            <Card>
              <CardHeader title="Versions de l'extraction" description="La proposition, puis chaque correction." />
              <ul className="space-y-2 px-5 py-4 text-muted">
                {doc.versions.map((v) => (
                  <li key={v.version} className="flex items-start gap-2">
                    <Badge tone={v.source === "AI" ? "navy" : "neutral"}>v{v.version}</Badge>
                    <span>
                      {v.source === "AI" ? `Proposition (${v.provider})` : `Correction par ${v.created_by?.full_name ?? "—"}`}
                      {v.changed.length > 0 && <span className="text-ink"> · {v.changed.length} champ(s) modifié(s)</span>}
                      <span className="block text-xs">{formatDateTime(v.created_at)}</span>
                    </span>
                  </li>
                ))}
              </ul>
            </Card>
          )}
        </div>
      </div>
    </>
  );
}

function FieldRow({ field, editable, draft, onChange }: { field: ExtractedField; editable: boolean; draft: string | undefined; onChange: (v: string) => void }) {
  const current = draft ?? (field.value == null ? "" : String(field.value));
  const missing = field.required && current.trim() === "";
  return (
    <div className="grid grid-cols-[1fr_auto] items-start gap-x-3 gap-y-1 border-b border-line pb-3 last:border-0 last:pb-0">
      <Label htmlFor={`f-${field.name}`} className="mb-0 self-center">
        {field.label}
        {field.required && <span className="text-danger"> *</span>}
      </Label>
      <div className="row-span-2 self-center">
        {field.corrected ? <Badge tone="navy">corrigé</Badge> : <ConfidenceDot value={field.confidence} />}
      </div>
      <div className="col-span-2">
        {editable ? (
          field.kind === "text" && field.name.includes("description") ? (
            <Textarea id={`f-${field.name}`} rows={2} value={current} aria-invalid={missing} onChange={(e) => onChange(e.target.value)} />
          ) : (
            <Input
              id={`f-${field.name}`}
              type={field.kind === "date" ? "date" : "text"}
              inputMode={field.kind === "amount" ? "decimal" : undefined}
              value={current}
              aria-invalid={missing}
              onChange={(e) => onChange(e.target.value)}
            />
          )
        ) : (
          <p className={current ? "" : "text-muted"}>{current || "—"}</p>
        )}
        {field.corrected && field.proposed != null && String(field.proposed) !== current && (
          <p className="mt-1 text-xs text-muted">Proposé : {String(field.proposed)}</p>
        )}
      </div>
    </div>
  );
}

function Actions({ doc, dirty, busy, hasBlocking, onValidate, onReject }: { doc: DocumentDetail; dirty: boolean; busy: boolean; hasBlocking: boolean; onValidate: () => void; onReject: (reason: string) => void }) {
  const [rejecting, setRejecting] = useState(false);
  const [reason, setReason] = useState("");
  if (rejecting) {
    return (
      <Card className="w-full max-w-sm space-y-2 p-3">
        <Label htmlFor="reject-reason">Motif du rejet</Label>
        <Textarea id="reject-reason" rows={2} value={reason} autoFocus onChange={(e) => setReason(e.target.value)} />
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={() => setRejecting(false)}>Annuler</Button>
          <Button disabled={busy || !reason.trim()} onClick={() => onReject(reason)}>Rejeter</Button>
        </div>
      </Card>
    );
  }
  return (
    <div className="flex flex-wrap items-center gap-2">
      <Button variant="secondary" disabled={busy} onClick={() => setRejecting(true)}>Rejeter</Button>
      <Button disabled={busy || dirty || hasBlocking} onClick={onValidate} title={dirty ? "Enregistrez d'abord les corrections" : hasBlocking ? "Levez les anomalies bloquantes" : undefined}>
        <CheckCircle2 className="size-4" aria-hidden /> Valider {doc.doc_type === "INVOICE" ? "la facture" : "la demande"}
      </Button>
    </div>
  );
}

function LinkCard({ doc, editable, busy, onLink }: { doc: DocumentDetail; editable: boolean; busy: boolean; onLink: (requestId: string | null) => void }) {
  const [options, setOptions] = useState<RequestRow[] | null>(null);
  const [picking, setPicking] = useState(false);

  useEffect(() => {
    if (picking && options === null) {
      api<{ items: RequestRow[] }>("/api/requests?open_only=true&page_size=100")
        .then((r) => setOptions(r.items))
        .catch(() => setOptions([]));
    }
  }, [picking, options]);

  return (
    <Card>
      <CardHeader title="Demande rattachée" description="Relier ce document à une demande (US-306)." />
      <div className="space-y-3 px-5 py-4">
        {doc.request ? (
          <p className="flex items-center gap-2">
            <Link2 className="size-4 text-muted" aria-hidden />
            <Link href={`/requests/${doc.request.id}`} className="font-medium text-navy-700 hover:underline">
              {doc.request.reference}
            </Link>
            <span className="truncate text-muted">{doc.request.title}</span>
          </p>
        ) : (
          <p className="flex items-center gap-2 text-muted"><FileText className="size-4" aria-hidden /> Aucune demande rattachée.</p>
        )}
        {editable &&
          (picking ? (
            <div className="flex gap-2">
              <Select aria-label="Choisir une demande" disabled={busy} defaultValue={doc.request?.id ?? ""} onChange={(e) => { onLink(e.target.value || null); setPicking(false); }}>
                <option value="">Aucune</option>
                {(options ?? []).map((r) => (
                  <option key={r.id} value={r.id}>{r.reference} — {r.title}</option>
                ))}
              </Select>
              <Button variant="ghost" onClick={() => setPicking(false)}>Fermer</Button>
            </div>
          ) : (
            <Button variant="secondary" disabled={busy} onClick={() => setPicking(true)}>
              {doc.request ? <><RotateCcw className="size-4" aria-hidden /> Changer</> : <><Link2 className="size-4" aria-hidden /> Rattacher</>}
            </Button>
          ))}
      </div>
    </Card>
  );
}
