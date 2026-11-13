"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Info, ShieldAlert } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { useSession } from "@/components/layout/session";
import { Card, CardHeader } from "@/components/ui/card";
import { EmptyState, ErrorMessage, Spinner } from "@/components/ui/feedback";
import { api } from "@/lib/api";
import { formatPercent } from "@/lib/labels";
import type { Quality } from "@/lib/types";
import { cn } from "@/lib/utils";

const FIELD_NAMES = { category: "Catégorie", priority: "Priorité", team: "Équipe" } as const;
const KEPT_NAMES = { category_id: "Catégorie", priority: "Priorité", team_id: "Équipe" } as const;

export default function QualityPage() {
  const me = useSession();
  const [q, setQ] = useState<Quality | null>(null);
  const [error, setError] = useState<string | null>(null);
  const allowed = me.role === "ADMIN" || me.role === "MANAGER";

  useEffect(() => {
    if (allowed) api<Quality>("/api/ai/triage/quality").then(setQ).catch((e: Error) => setError(e.message));
  }, [allowed]);

  if (!allowed) {
    return (
      <Card>
        <EmptyState icon={ShieldAlert} title="Accès réservé">
          La qualité du tri est suivie par les responsables et les administrateurs.
        </EmptyState>
      </Card>
    );
  }

  return (
    <>
      <Link href="/requests" className="mb-3 inline-flex items-center gap-1 text-muted hover:text-ink">
        <ArrowLeft className="size-4" aria-hidden /> Demandes
      </Link>
      <PageHeader
        title="Qualité du tri assisté"
        description="Ce que vaut la proposition de catégorie, priorité et équipe, mesuré deux fois : sur un jeu étiqueté et sur les décisions des équipes."
      />
      {error && <ErrorMessage message={error} />}
      {!q ? (
        <Spinner />
      ) : (
        <div className="space-y-6">
          <Card>
            <CardHeader
              title="Jeu de test étiqueté"
              description={`${q.offline.size} demandes synthétiques jamais utilisées pour régler les règles · ${q.offline.provider}`}
            />
            <div className="grid gap-4 px-5 py-4 sm:grid-cols-4">
              {q.offline.fields.map((f) => (
                <Score key={f.field} label={FIELD_NAMES[f.field]} value={f.accuracy} detail={`${f.correct} / ${f.total}`} />
              ))}
              <Score label="Les trois justes" value={q.offline.all_three_correct} detail="demande entièrement bien triée" />
            </div>
            <p className="flex items-start gap-2 border-t border-line px-5 py-3 text-muted">
              <Info className="mt-0.5 size-4 shrink-0" aria-hidden />
              Mode démonstration : des règles par mots-clés. Sur les exemples qui ont servi à les écrire, elles trient entièrement bien{" "}
              {formatPercent(q.dev_all_three_correct)} des demandes, contre {formatPercent(q.offline.all_three_correct)} sur ce jeu de test : elles généralisent mal. C&apos;est la référence à battre
              par un modèle de langage, mesuré sur le même jeu (python -m app.ai.evaluate --provider claude).
            </p>
          </Card>

          <Card>
            <CardHeader title="Erreurs sur le jeu de test" description="Attendu par l'étiquette, puis obtenu." />
            {q.offline.errors.length === 0 ? (
              <p className="px-5 py-4 text-muted">Aucune erreur.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left">
                  <thead className="border-b border-line text-xs uppercase tracking-wide text-muted">
                    <tr>
                      <th className="px-5 py-2.5 font-medium">Demande</th>
                      <th className="px-5 py-2.5 font-medium">Attendu</th>
                      <th className="px-5 py-2.5 font-medium">Obtenu</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line">
                    {q.offline.errors.map((e) => (
                      <tr key={e.id}>
                        <td className="px-5 py-2.5">
                          <span className="text-muted">{e.id}</span> {e.title ?? e.error}
                        </td>
                        <td className="px-5 py-2.5 font-mono text-xs">{e.expected}</td>
                        <td className="px-5 py-2.5 font-mono text-xs">{e.predicted}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>

          <Card>
            <CardHeader
              title="Décisions des équipes"
              description={`${q.live.decided} propositions traitées dans cette organisation (données de démonstration simulées)`}
            />
            <div className="grid gap-4 px-5 py-4 sm:grid-cols-3">
              <Count label="Acceptées telles quelles" value={q.live.accepted} total={q.live.decided} />
              <Count label="Corrigées" value={q.live.modified} total={q.live.decided} />
              <Count label="Rejetées" value={q.live.rejected} total={q.live.decided} />
            </div>
            <div className="grid gap-4 border-t border-line px-5 py-4 sm:grid-cols-3">
              {(Object.keys(KEPT_NAMES) as (keyof typeof KEPT_NAMES)[]).map((k) => (
                <Score key={k} label={`${KEPT_NAMES[k]} conservée`} value={q.live.field_kept[k]} detail="parmi les propositions appliquées" />
              ))}
            </div>
          </Card>
        </div>
      )}
    </>
  );
}

function Score({ label, value, detail }: { label: string; value: number; detail: string }) {
  return (
    <div>
      <p className="text-muted">{label}</p>
      <p className={cn("mt-1 text-2xl font-semibold tabular-nums", value < 0.6 ? "text-danger" : value < 0.8 ? "text-warning" : "text-success")}>
        {formatPercent(value)}
      </p>
      <p className="text-xs text-muted">{detail}</p>
    </div>
  );
}

function Count({ label, value, total }: { label: string; value: number; total: number }) {
  return (
    <div>
      <p className="text-muted">{label}</p>
      <p className="mt-1 text-2xl font-semibold tabular-nums">{value}</p>
      <p className="text-xs text-muted">{total ? formatPercent(value / total) : "—"}</p>
    </div>
  );
}
