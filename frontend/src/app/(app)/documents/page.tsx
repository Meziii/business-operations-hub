"use client";

import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FileText, Search, Upload, X } from "lucide-react";
import { AnomalySummary, DocStatusBadge, OcrTag } from "@/components/documents/badges";
import { PageHeader } from "@/components/layout/page-header";
import { useSession } from "@/components/layout/session";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState, ErrorMessage, Spinner } from "@/components/ui/feedback";
import { Input, Label, Select } from "@/components/ui/input";
import { ApiError, api } from "@/lib/api";
import { DOC_TYPE_LABELS, formatDateTime } from "@/lib/labels";
import type { DocumentDetail, DocumentPage, DocumentStats, DocType } from "@/lib/types";
import { cn } from "@/lib/utils";

const FILTER_KEYS = ["q", "status", "doc_type", "blocking_only", "page"] as const;
const amount = new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" });

export default function DocumentsPage() {
  return (
    <Suspense fallback={<Spinner />}>
      <DocumentsView />
    </Suspense>
  );
}

function DocumentsView() {
  const me = useSession();
  const router = useRouter();
  const params = useSearchParams();
  const [data, setData] = useState<DocumentPage | null>(null);
  const [stats, setStats] = useState<DocumentStats | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState(params.get("q") ?? "");

  const query = useMemo(() => {
    const q = new URLSearchParams();
    for (const k of FILTER_KEYS) {
      const v = params.get(k);
      if (v) q.set(k, v);
    }
    return q;
  }, [params]);

  const setFilter = useCallback(
    (key: string, value: string | null) => {
      const next = new URLSearchParams(query);
      if (value) next.set(key, value);
      else next.delete(key);
      if (key !== "page") next.delete("page");
      router.replace(`/documents${next.size ? `?${next}` : ""}`);
    },
    [query, router],
  );

  const reload = useCallback(() => {
    api<DocumentStats>("/api/documents/stats").then(setStats).catch((e: Error) => setError(e.message));
  }, []);

  useEffect(reload, [reload]);
  useEffect(() => {
    setData(null);
    api<DocumentPage>(`/api/documents?${query}`)
      .then(setData)
      .catch((e: Error) => setError(e.message));
  }, [query]);

  useEffect(() => {
    const current = params.get("q") ?? "";
    if (search === current) return;
    const t = setTimeout(() => setFilter("q", search.trim() || null), 300);
    return () => clearTimeout(t);
  }, [search, params, setFilter]);

  const active = (k: string, v: string) => query.get(k) === v;
  const hasFilters = FILTER_KEYS.some((k) => k !== "page" && query.get(k));
  const page = Number(query.get("page") ?? 1);
  const pages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;

  return (
    <>
      <PageHeader title="Documents" description="Extraire, contrôler et valider factures et demandes de garantie.">
        <div className="flex gap-2">
          {(me.role === "ADMIN" || me.role === "MANAGER") && (
            <Link href="/documents/quality">
              <Button variant="secondary">Qualité de l&apos;extraction</Button>
            </Link>
          )}
          {me.role !== "VIEWER" && <UploadButton onDone={reload} />}
        </div>
      </PageHeader>

      {error && <ErrorMessage message={error} />}

      <div className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <KpiTile label="À vérifier" value={stats?.to_review} onClick={() => setFilter("status", active("status", "TO_REVIEW") ? null : "TO_REVIEW")} selected={active("status", "TO_REVIEW")} />
        <KpiTile label="Anomalie bloquante" value={stats?.with_blocking} tone="danger" onClick={() => setFilter("blocking_only", active("blocking_only", "true") ? null : "true")} selected={active("blocking_only", "true")} />
        <KpiTile label="Validés" value={stats?.validated} tone="success" onClick={() => setFilter("status", active("status", "VALIDATED") ? null : "VALIDATED")} selected={active("status", "VALIDATED")} />
        <KpiTile label="Rejetés" value={stats?.rejected} onClick={() => setFilter("status", active("status", "REJECTED") ? null : "REJECTED")} selected={active("status", "REJECTED")} />
      </div>

      <Card>
        <div className="flex flex-wrap items-center gap-2 border-b border-line p-3">
          <div className="relative min-w-52 flex-1">
            <Search className="pointer-events-none absolute top-2.5 left-2.5 size-4 text-muted" aria-hidden />
            <Input aria-label="Rechercher" placeholder="Référence, fichier, valeur…" className="pl-8" value={search} onChange={(e) => setSearch(e.target.value)} />
          </div>
          <Select aria-label="Type" className="w-auto" value={query.get("doc_type") ?? ""} onChange={(e) => setFilter("doc_type", e.target.value || null)}>
            <option value="">Tous les types</option>
            <option value="INVOICE">Factures</option>
            <option value="WARRANTY_CLAIM">Demandes de garantie</option>
          </Select>
          {hasFilters && (
            <Button variant="ghost" onClick={() => { setSearch(""); router.replace("/documents"); }}>
              <X className="size-4" aria-hidden /> Effacer
            </Button>
          )}
        </div>

        {!data ? (
          <Spinner />
        ) : data.items.length === 0 ? (
          <EmptyState icon={FileText} title={hasFilters ? "Aucun document ne correspond" : "Aucun document"}>
            {hasFilters ? "Modifiez ou effacez les filtres." : "Importez une facture ou une demande de garantie."}
          </EmptyState>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead className="border-b border-line text-xs tracking-wide text-muted uppercase">
                <tr>
                  <th className="px-5 py-2.5 font-medium">Document</th>
                  <th className="px-3 py-2.5 font-medium">Type</th>
                  <th className="px-3 py-2.5 font-medium">Statut</th>
                  <th className="px-3 py-2.5 font-medium">Contrôles</th>
                  <th className="px-3 py-2.5 text-right font-medium">Montant</th>
                  <th className="px-5 py-2.5 font-medium">Importé</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((d) => (
                  <tr key={d.id} className="border-b border-line last:border-0 hover:bg-canvas">
                    <td className="px-5 py-3">
                      <Link href={`/documents/${d.id}`} className="font-medium text-navy-700 hover:underline">
                        {d.summary}
                      </Link>
                      <p className="flex items-center gap-2 text-xs text-muted">
                        {d.reference}
                        {d.ocr_used && <OcrTag />}
                        {d.request && <span>· {d.request.reference}</span>}
                      </p>
                    </td>
                    <td className="px-3 py-3 text-muted">{DOC_TYPE_LABELS[d.doc_type]}</td>
                    <td className="px-3 py-3"><DocStatusBadge status={d.status} /></td>
                    <td className="px-3 py-3">
                      {d.status === "TO_REVIEW" ? <AnomalySummary blocking={d.blocking} warnings={d.warnings} /> : <span className="text-muted">—</span>}
                    </td>
                    <td className="px-3 py-3 text-right tabular-nums">{d.amount != null ? amount.format(d.amount) : "—"}</td>
                    <td className="px-5 py-3 text-muted">{formatDateTime(d.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {data && pages > 1 && (
          <div className="flex items-center justify-between border-t border-line p-3 text-muted">
            <span>{data.total} documents</span>
            <div className="flex items-center gap-2">
              <Button variant="secondary" disabled={page <= 1} onClick={() => setFilter("page", String(page - 1))}>Précédent</Button>
              <span className="tabular-nums">{page} / {pages}</span>
              <Button variant="secondary" disabled={page >= pages} onClick={() => setFilter("page", String(page + 1))}>Suivant</Button>
            </div>
          </div>
        )}
      </Card>
    </>
  );
}

function UploadButton({ onDone }: { onDone: () => void }) {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [docType, setDocType] = useState<DocType>("INVOICE");
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function send(file: File) {
    setBusy(true);
    setError(null);
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("doc_type", docType);
      const res = await fetch("/api/documents", { method: "POST", body: form, credentials: "same-origin" });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new ApiError(res.status, typeof body.detail === "string" ? body.detail : "Import impossible.");
      }
      const doc: DocumentDetail = await res.json();
      onDone();
      router.push(`/documents/${doc.id}`);
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  }

  return (
    <div className="relative">
      <Button onClick={() => setOpen((v) => !v)} aria-expanded={open}>
        <Upload className="size-4" aria-hidden /> Importer un PDF
      </Button>
      {open && (
        <Card className="absolute right-0 z-10 mt-2 w-80 space-y-3 p-4 shadow-lg">
          <div>
            <Label htmlFor="up-type">Type de document</Label>
            <Select id="up-type" value={docType} onChange={(e) => setDocType(e.target.value as DocType)} disabled={busy}>
              <option value="INVOICE">Facture</option>
              <option value="WARRANTY_CLAIM">Demande de garantie</option>
            </Select>
          </div>
          {error && <ErrorMessage message={error} />}
          <input
            ref={inputRef}
            type="file"
            accept="application/pdf"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              e.target.value = "";
              if (file) void send(file);
            }}
          />
          <Button className="w-full" disabled={busy} onClick={() => inputRef.current?.click()}>
            {busy ? "Lecture et extraction…" : "Choisir un fichier PDF"}
          </Button>
          <p className="text-xs text-muted">PDF uniquement, 10 Mo maximum. Les scans sont lus par OCR.</p>
        </Card>
      )}
    </div>
  );
}

function KpiTile({ label, value, tone, selected, onClick }: { label: string; value: number | undefined; tone?: "danger" | "success"; selected: boolean; onClick: () => void }) {
  return (
    <button onClick={onClick} aria-pressed={selected} className={cn("rounded-[var(--radius-card)] border bg-surface p-4 text-left transition-colors hover:border-navy-200", selected ? "border-navy-600 ring-2 ring-navy-100" : "border-line")}>
      <p className="text-muted">{label}</p>
      <p className={cn("mt-1 text-2xl font-semibold tabular-nums", value && tone === "danger" ? "text-danger" : value && tone === "success" ? "text-success" : "text-ink")}>{value ?? "…"}</p>
    </button>
  );
}
