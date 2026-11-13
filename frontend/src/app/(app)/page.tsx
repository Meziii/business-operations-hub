"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { NAV } from "@/components/layout/nav";
import { useSession } from "@/components/layout/session";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader } from "@/components/ui/card";
import { api } from "@/lib/api";
import type { Health, RequestStats } from "@/lib/types";

/** Phase de livraison des modules pas encore disponibles. */
const PLANNED: Record<string, number> = { "/documents": 3, "/assistant": 4, "/analytics": 5 };

function requestsSummary(stats: RequestStats | null, failed: boolean): string {
  if (failed) return "Indicateurs indisponibles";
  if (!stats) return "…";
  const parts = [`${stats.open} ouverte${stats.open > 1 ? "s" : ""}`];
  if (stats.overdue) parts.push(`${stats.overdue} en retard`);
  if (stats.to_classify) parts.push(`${stats.to_classify} à classer`);
  return parts.join(" · ");
}

export default function OverviewPage() {
  const me = useSession();
  const [health, setHealth] = useState<Health | null>(null);
  const [healthError, setHealthError] = useState(false);
  const [stats, setStats] = useState<RequestStats | null>(null);
  const [statsError, setStatsError] = useState(false);

  useEffect(() => {
    api<Health>("/api/health").then(setHealth).catch(() => setHealthError(true));
    api<RequestStats>("/api/requests/stats").then(setStats).catch(() => setStatsError(true));
  }, []);

  const modules = NAV.filter((i) => i.href === "/requests" || i.href in PLANNED);

  return (
    <>
      <PageHeader
        title={`Bonjour ${me.full_name.split(" ")[0]}`}
        description="Où en sont les modules, sur votre périmètre."
      />

      <div className="grid gap-4 md:grid-cols-2">
        {modules.map(({ href, label, icon: Icon }) => (
          <Link key={href} href={href} className="group">
            <Card className="flex h-full items-center gap-4 p-5 transition-colors group-hover:border-navy-200">
              <div className="rounded-md bg-navy-50 p-2.5 text-navy-700">
                <Icon className="size-5" aria-hidden />
              </div>
              <div className="flex-1">
                <p className="font-semibold">{label}</p>
                <p className={stats?.overdue && href === "/requests" ? "text-danger" : "text-muted"}>
                  {href === "/requests" ? requestsSummary(stats, statsError) : `Prévu en phase ${PLANNED[href]}`}
                </p>
              </div>
              <ArrowRight className="size-4 text-muted group-hover:text-navy-700" aria-hidden />
            </Card>
          </Link>
        ))}
      </div>

      <Card className="mt-6">
        <CardHeader title="État de la plateforme" description="Vérifié en direct auprès de l'API." />
        <dl className="grid gap-4 px-5 py-4 sm:grid-cols-3">
          <div>
            <dt className="text-muted">API</dt>
            <dd className="mt-1">
              {healthError ? <Badge tone="danger">Injoignable</Badge> : health ? <Badge tone="success">En ligne</Badge> : "…"}
            </dd>
          </div>
          <div>
            <dt className="text-muted">Base de données</dt>
            <dd className="mt-1">{health ? <Badge tone="success">Connectée</Badge> : healthError ? "—" : "…"}</dd>
          </div>
          <div>
            <dt className="text-muted">Fournisseur d&apos;IA</dt>
            <dd className="mt-1">
              {health ? (
                <Badge tone={health.ai_provider.startsWith("mock") ? "warning" : "navy"}>
                  {health.ai_provider.startsWith("mock") ? "Mode démonstration (règles)" : health.ai_provider}
                </Badge>
              ) : (
                "…"
              )}
            </dd>
          </div>
        </dl>
      </Card>
    </>
  );
}
