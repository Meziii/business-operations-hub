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
import type { Health } from "@/lib/types";

const PHASE: Record<string, number> = { "/requests": 2, "/documents": 3, "/assistant": 4, "/analytics": 5 };

export default function OverviewPage() {
  const me = useSession();
  const [health, setHealth] = useState<Health | null>(null);
  const [healthError, setHealthError] = useState(false);

  useEffect(() => {
    api<Health>("/api/health").then(setHealth).catch(() => setHealthError(true));
  }, []);

  const modules = NAV.filter((i) => i.href in PHASE);

  return (
    <>
      <PageHeader
        title={`Bonjour ${me.full_name.split(" ")[0]}`}
        description="Les indicateurs apparaîtront ici dès que les modules produiront des données."
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
                <p className="text-muted">Prévu en phase {PHASE[href]}</p>
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
                <Badge tone={health.ai_provider === "mock" ? "warning" : "navy"}>
                  {health.ai_provider === "mock" ? "Mode démonstration" : health.ai_provider}
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
