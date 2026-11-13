"use client";

import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Gauge, Inbox, Plus, Search, X } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { useSession } from "@/components/layout/session";
import { PriorityLabel, SlaIndicator, StatusBadge } from "@/components/requests/badges";
import { Button } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { EmptyState, ErrorMessage, Spinner } from "@/components/ui/feedback";
import { Input, Select } from "@/components/ui/input";
import { api } from "@/lib/api";
import { PRIORITIES, PRIORITY_LABELS, STATUSES, STATUS_LABELS, formatDateTime } from "@/lib/labels";
import type { ReferenceData, RequestPage, RequestStats } from "@/lib/types";
import { cn } from "@/lib/utils";

const FILTER_KEYS = ["q", "status", "priority", "category_id", "team_id", "assignee", "overdue", "open_only", "page"] as const;

export default function RequestsPage() {
  return (
    <Suspense fallback={<Spinner />}>
      <RequestsView />
    </Suspense>
  );
}

function RequestsView() {
  const me = useSession();
  const router = useRouter();
  const params = useSearchParams();
  const [data, setData] = useState<RequestPage | null>(null);
  const [stats, setStats] = useState<RequestStats | null>(null);
  const [ref, setRef] = useState<ReferenceData | null>(null);
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
      router.replace(`/requests${next.size ? `?${next}` : ""}`);
    },
    [query, router],
  );

  useEffect(() => {
    api<ReferenceData>("/api/reference").then(setRef).catch((e: Error) => setError(e.message));
    api<RequestStats>("/api/requests/stats").then(setStats).catch((e: Error) => setError(e.message));
  }, []);

  useEffect(() => {
    setData(null);
    api<RequestPage>(`/api/requests?${query}`)
      .then(setData)
      .catch((e: Error) => setError(e.message));
  }, [query]);

  // Recherche : on attend la fin de la frappe.
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
  const canCreate = me.role !== "VIEWER";

  return (
    <>
      <PageHeader title="Demandes" description="Centraliser, prioriser et suivre les demandes des clients et partenaires.">
        <div className="flex gap-2">
          {(me.role === "ADMIN" || me.role === "MANAGER") && (
            <Link href="/requests/quality">
              <Button variant="secondary">
                <Gauge className="size-4" aria-hidden /> Qualité du tri IA
              </Button>
            </Link>
          )}
          {canCreate && (
            <Link href="/requests/new">
              <Button>
                <Plus className="size-4" aria-hidden /> Nouvelle demande
              </Button>
            </Link>
          )}
        </div>
      </PageHeader>

      {error && <ErrorMessage message={error} />}

      <div className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <KpiTile label="Ouvertes" value={stats?.open} onClick={() => setFilter("open_only", active("open_only", "true") ? null : "true")} selected={active("open_only", "true")} />
        <KpiTile label="En retard" value={stats?.overdue} tone="danger" onClick={() => setFilter("overdue", active("overdue", "true") ? null : "true")} selected={active("overdue", "true")} />
        <KpiTile label="À classer" value={stats?.to_classify} tone="warning" onClick={() => setFilter("status", active("status", "NEW") ? null : "NEW")} selected={active("status", "NEW")} />
        <KpiTile label="En attente d'infos" value={stats?.waiting_info} onClick={() => setFilter("status", active("status", "WAITING_INFO") ? null : "WAITING_INFO")} selected={active("status", "WAITING_INFO")} />
      </div>

      {(me.role === "ADMIN" || me.role === "MANAGER") && stats && stats.by_team.length > 0 && (
        <TeamLoad
          rows={stats.by_team}
          selectedTeam={query.get("team_id")}
          onSelect={(id) => setFilter("team_id", query.get("team_id") === id ? null : id)}
        />
      )}

      <Card>
        <div className="flex flex-wrap items-center gap-2 border-b border-line p-3">
          <div className="relative min-w-52 flex-1">
            <Search className="pointer-events-none absolute top-2.5 left-2.5 size-4 text-muted" aria-hidden />
            <Input
              aria-label="Rechercher"
              placeholder="Référence, titre, client…"
              className="pl-8"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <Select aria-label="Statut" className="w-auto" value={query.get("status") ?? ""} onChange={(e) => setFilter("status", e.target.value || null)}>
            <option value="">Tous les statuts</option>
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {STATUS_LABELS[s]}
              </option>
            ))}
          </Select>
          <Select aria-label="Priorité" className="w-auto" value={query.get("priority") ?? ""} onChange={(e) => setFilter("priority", e.target.value || null)}>
            <option value="">Toutes priorités</option>
            {PRIORITIES.map((p) => (
              <option key={p} value={p}>
                {PRIORITY_LABELS[p]}
              </option>
            ))}
          </Select>
          <Select aria-label="Catégorie" className="w-auto" value={query.get("category_id") ?? ""} onChange={(e) => setFilter("category_id", e.target.value || null)}>
            <option value="">Toutes catégories</option>
            {ref?.categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </Select>
          <Select aria-label="Équipe" className="w-auto" value={query.get("team_id") ?? ""} onChange={(e) => setFilter("team_id", e.target.value || null)}>
            <option value="">Toutes équipes</option>
            {ref?.teams.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </Select>
          {me.role !== "VIEWER" && (
            <Button variant={active("assignee", "me") ? "primary" : "secondary"} onClick={() => setFilter("assignee", active("assignee", "me") ? null : "me")}>
              Mes demandes
            </Button>
          )}
          {hasFilters && (
            <Button
              variant="ghost"
              onClick={() => {
                setSearch("");
                router.replace("/requests");
              }}
            >
              <X className="size-4" aria-hidden /> Effacer
            </Button>
          )}
        </div>

        {!data ? (
          <Spinner />
        ) : data.items.length === 0 ? (
          <EmptyState icon={Inbox} title={hasFilters ? "Aucune demande ne correspond" : "Aucune demande"}>
            {hasFilters ? "Modifiez ou effacez les filtres." : "Les nouvelles demandes apparaîtront ici."}
          </EmptyState>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead className="border-b border-line text-xs uppercase tracking-wide text-muted">
                  <tr>
                    <th className="px-4 py-2.5 font-medium">Demande</th>
                    <th className="px-4 py-2.5 font-medium">Client</th>
                    <th className="px-4 py-2.5 font-medium">Statut</th>
                    <th className="px-4 py-2.5 font-medium">Priorité</th>
                    <th className="hidden px-4 py-2.5 font-medium xl:table-cell">Équipe</th>
                    <th className="hidden px-4 py-2.5 font-medium md:table-cell">Affectée à</th>
                    <th className="px-4 py-2.5 font-medium">Échéance</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {data.items.map((r) => (
                    <tr key={r.id} className="cursor-pointer hover:bg-canvas" onClick={() => router.push(`/requests/${r.id}`)}>
                      <td className="max-w-80 px-4 py-3">
                        <Link href={`/requests/${r.id}`} className="font-medium text-ink hover:underline" onClick={(e) => e.stopPropagation()}>
                          {r.title}
                        </Link>
                        <p className="text-xs text-muted">
                          {r.reference} · {formatDateTime(r.created_at)}
                        </p>
                      </td>
                      <td className="px-4 py-3">{r.account.name}</td>
                      <td className="px-4 py-3">
                        <StatusBadge status={r.status} />
                      </td>
                      <td className="px-4 py-3">
                        <PriorityLabel priority={r.priority} />
                      </td>
                      <td className="hidden px-4 py-3 xl:table-cell">{r.team?.name ?? <span className="text-muted">—</span>}</td>
                      <td className="hidden px-4 py-3 md:table-cell">{r.assignee?.full_name ?? <span className="text-muted">—</span>}</td>
                      <td className="px-4 py-3">
                        <SlaIndicator state={r.sla_state} due={r.sla_next_due} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="flex items-center justify-between border-t border-line px-4 py-3 text-muted">
              <span>
                {data.total} demande{data.total > 1 ? "s" : ""}
              </span>
              {pages > 1 && (
                <div className="flex items-center gap-2">
                  <Button variant="secondary" disabled={page <= 1} onClick={() => setFilter("page", String(page - 1))}>
                    Précédent
                  </Button>
                  <span>
                    {page} / {pages}
                  </span>
                  <Button variant="secondary" disabled={page >= pages} onClick={() => setFilter("page", String(page + 1))}>
                    Suivant
                  </Button>
                </div>
              )}
            </div>
          </>
        )}
      </Card>
    </>
  );
}

/** US-107 : charge et retards par équipe, pour arbitrer les affectations. */
function TeamLoad({
  rows,
  selectedTeam,
  onSelect,
}: {
  rows: RequestStats["by_team"];
  selectedTeam: string | null;
  onSelect: (teamId: string) => void;
}) {
  return (
    <Card className="mb-6">
      <CardHeader title="Charge des équipes" description="Demandes ouvertes, en retard et sans personne affectée. Cliquer sur une équipe filtre la liste." />
      <div className="overflow-x-auto">
        <table className="w-full text-left">
          <thead className="text-xs tracking-wide text-muted uppercase">
            <tr className="border-b border-line">
              <th className="px-5 py-2 font-medium">Équipe</th>
              <th className="px-3 py-2 text-right font-medium">Ouvertes</th>
              <th className="px-3 py-2 text-right font-medium">En retard</th>
              <th className="px-5 py-2 text-right font-medium">Non affectées</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr
                key={r.team.id}
                className={cn("border-b border-line last:border-0", selectedTeam === r.team.id && "bg-navy-50")}
              >
                <td className="px-5 py-2">
                  <button
                    onClick={() => onSelect(r.team.id)}
                    aria-pressed={selectedTeam === r.team.id}
                    className="font-medium text-navy-700 hover:underline"
                  >
                    {r.team.name}
                  </button>
                </td>
                <td className="px-3 py-2 text-right tabular-nums">{r.open}</td>
                <td className={cn("px-3 py-2 text-right tabular-nums", r.overdue > 0 && "font-semibold text-danger")}>
                  {r.overdue}
                </td>
                <td className={cn("px-5 py-2 text-right tabular-nums", r.unassigned > 0 && "text-warning")}>
                  {r.unassigned}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

function KpiTile({
  label,
  value,
  tone,
  selected,
  onClick,
}: {
  label: string;
  value: number | undefined;
  tone?: "danger" | "warning";
  selected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      aria-pressed={selected}
      className={cn(
        "rounded-[var(--radius-card)] border bg-surface p-4 text-left transition-colors hover:border-navy-200",
        selected ? "border-navy-600 ring-2 ring-navy-100" : "border-line",
      )}
    >
      <p className="text-muted">{label}</p>
      <p
        className={cn(
          "mt-1 text-2xl font-semibold tabular-nums",
          value && tone === "danger" ? "text-danger" : value && tone === "warning" ? "text-warning" : "text-ink",
        )}
      >
        {value ?? "…"}
      </p>
    </button>
  );
}
