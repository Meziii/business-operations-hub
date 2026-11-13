"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Info } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { Card, CardHeader } from "@/components/ui/card";
import { ErrorMessage, Spinner } from "@/components/ui/feedback";
import { ApiError, api } from "@/lib/api";
import { formatPercent } from "@/lib/labels";
import type { DocQuality } from "@/lib/types";

export default function DocumentQualityPage() {
  const [q, setQ] = useState<DocQuality | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [denied, setDenied] = useState(false);

  useEffect(() => {
    api<DocQuality>("/api/ai/extraction/quality")
      .then(setQ)
      .catch((e: Error) => (e instanceof ApiError && e.status === 403 ? setDenied(true) : setError(e.message)));
  }, []);

  if (denied)
    return <PageHeader title="Accès réservé" description="La qualité de l'extraction est suivie par les responsables et les administrateurs." />;
  if (!q) return error ? <ErrorMessage message={error} /> : <Spinner />;

  const o = q.offline;
  const pct = (x: number | null) => (x == null ? "—" : formatPercent(x));

  return (
    <>
      <Link href="/documents" className="mb-3 inline-flex items-center gap-1 text-muted hover:text-ink">
        <ArrowLeft className="size-4" aria-hidden /> Documents
      </Link>
      <PageHeader title="Qualité de l'extraction" description="Ce que valent les champs extraits, mesuré sur un jeu étiqueté et sur les décisions des équipes." />

      <Card className="mb-6">
        <CardHeader title="Jeu de test étiqueté" description={`${o.evaluated} documents synthétiques jamais utilisés pour écrire les règles · ${o.provider}`} />
        <div className="grid grid-cols-2 gap-px bg-line sm:grid-cols-4">
          <Stat label="Documents entièrement justes" value={formatPercent(o.documents_fully_correct)} tone="strong" />
          <Stat label="Par champ — PDF texte" value={pct(o.text_accuracy)} />
          <Stat label="Par champ — scans (OCR)" value={pct(o.scan_accuracy)} />
          <Stat label="Anomalies détectées" value={`${o.anomalies.detected}/${o.anomalies.expected}`} sub={`${o.anomalies.false_alarms} fausses alertes`} />
        </div>
        <p className="flex items-start gap-2 border-t border-line px-5 py-3 text-muted">
          <Info className="mt-0.5 size-4 shrink-0" aria-hidden />
          Mode démonstration : des règles par libellés. Sur les documents qui ont servi à les écrire, elles lisent
          entièrement bien {formatPercent(q.dev_documents_fully_correct)} des documents, contre{" "}
          {formatPercent(o.documents_fully_correct)} sur ce jeu de test. Elles réussissent les mises en page connues
          et échouent sur une mise en page nouvelle — c&apos;est la référence à battre par un modèle de langage, mesuré
          sur le même jeu (<code>python -m app.modules.documents.evaluate --provider claude</code>).
        </p>
      </Card>

      <Card className="mb-6">
        <CardHeader title="Exactitude par mise en page" description="100 % sur les mises en page connues ; l'écart révèle ce qui ne généralise pas." />
        <div className="grid grid-cols-2 gap-px bg-line sm:grid-cols-3 lg:grid-cols-5">
          {Object.entries(o.by_layout).map(([layout, acc]) => (
            <Stat key={layout} label={layout} value={formatPercent(acc)} tone={acc < 0.5 ? "weak" : undefined} />
          ))}
        </div>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader title="Exactitude par champ" description="Sur le jeu de test." />
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead className="border-b border-line text-xs tracking-wide text-muted uppercase">
                <tr><th className="px-5 py-2 font-medium">Champ</th><th className="px-3 py-2 text-right font-medium">Correct</th><th className="px-5 py-2 text-right font-medium">Exactitude</th></tr>
              </thead>
              <tbody>
                {o.fields.map((f) => (
                  <tr key={f.field} className="border-b border-line last:border-0">
                    <td className="px-5 py-2">{f.label}</td>
                    <td className="px-3 py-2 text-right tabular-nums text-muted">{f.correct}/{f.total}</td>
                    <td className="px-5 py-2 text-right tabular-nums">{formatPercent(f.accuracy)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        <Card>
          <CardHeader title="Décisions des équipes" description={`${q.live.decided} extractions traitées dans cette organisation (démonstration simulée)`} />
          {q.live.decided === 0 ? (
            <p className="px-5 py-4 text-muted">Aucune décision pour l&apos;instant.</p>
          ) : (
            <>
              <div className="grid grid-cols-3 gap-px bg-line">
                <Stat label="Validées sans retouche" value={String(q.live.accepted)} sub={formatPercent(q.live.accepted / q.live.decided)} />
                <Stat label="Corrigées" value={String(q.live.modified)} sub={formatPercent(q.live.modified / q.live.decided)} />
                <Stat label="Rejetées" value={String(q.live.rejected)} sub={formatPercent(q.live.rejected / q.live.decided)} />
              </div>
              {Object.keys(q.live.field_kept).length > 0 && (
                <div className="px-5 py-4">
                  <p className="mb-2 text-muted">Champs conservés tels quels, parmi les documents appliqués :</p>
                  <ul className="space-y-1">
                    {Object.entries(q.live.field_kept).map(([name, kept]) => (
                      <li key={name} className="flex justify-between"><span className="text-muted">{name}</span><span className="tabular-nums">{formatPercent(kept)}</span></li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          )}
        </Card>
      </div>
    </>
  );
}

function Stat({ label, value, sub, tone }: { label: string; value: string; sub?: string; tone?: "strong" | "weak" }) {
  return (
    <div className="bg-surface px-5 py-4">
      <p className="text-muted">{label}</p>
      <p className={`mt-1 text-2xl font-semibold tabular-nums ${tone === "strong" ? "text-navy-700" : tone === "weak" ? "text-danger" : "text-ink"}`}>{value}</p>
      {sub && <p className="text-xs text-muted">{sub}</p>}
    </div>
  );
}
