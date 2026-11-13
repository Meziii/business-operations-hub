"use client";

import { useEffect, useState } from "react";
import { ShieldAlert } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { useSession } from "@/components/layout/session";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader } from "@/components/ui/card";
import { EmptyState, ErrorMessage, Spinner } from "@/components/ui/feedback";
import { api } from "@/lib/api";
import { ROLE_LABELS, type AuditEntry, type TeamWithCount, type User } from "@/lib/types";

const dateFmt = new Intl.DateTimeFormat("fr-FR", { dateStyle: "short", timeStyle: "short" });

export default function AdminPage() {
  const me = useSession();
  const [users, setUsers] = useState<User[] | null>(null);
  const [teams, setTeams] = useState<TeamWithCount[] | null>(null);
  const [audit, setAudit] = useState<AuditEntry[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const allowed = me.role === "ADMIN" || me.role === "MANAGER";

  useEffect(() => {
    if (!allowed) return;
    const fail = (e: Error) => setError(e.message);
    api<User[]>("/api/admin/users").then(setUsers).catch(fail);
    api<TeamWithCount[]>("/api/admin/teams").then(setTeams).catch(fail);
    if (me.role === "ADMIN") api<AuditEntry[]>("/api/admin/audit?limit=20").then(setAudit).catch(fail);
  }, [allowed, me.role]);

  if (!allowed) {
    return (
      <Card>
        <EmptyState icon={ShieldAlert} title="Accès réservé">
          L&apos;administration est réservée aux administrateurs et aux responsables.
        </EmptyState>
      </Card>
    );
  }

  return (
    <>
      <PageHeader title="Administration" description="Utilisateurs, équipes et journal des actions sensibles." />
      {error && <ErrorMessage message={error} />}

      <div className="grid gap-6 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <CardHeader title="Utilisateurs" description={users ? `${users.length} comptes` : undefined} />
          {!users ? (
            <Spinner />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead className="border-b border-line text-xs uppercase tracking-wide text-muted">
                  <tr>
                    <th className="px-5 py-2.5 font-medium">Nom</th>
                    <th className="px-5 py-2.5 font-medium">Rôle</th>
                    <th className="px-5 py-2.5 font-medium">Équipes</th>
                    <th className="px-5 py-2.5 font-medium">Statut</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {users.map((u) => (
                    <tr key={u.id}>
                      <td className="px-5 py-3">
                        <p className="font-medium">{u.full_name}</p>
                        <p className="text-muted">{u.email}</p>
                      </td>
                      <td className="px-5 py-3">{ROLE_LABELS[u.role]}</td>
                      <td className="px-5 py-3">{u.teams.map((t) => t.name).join(", ") || "—"}</td>
                      <td className="px-5 py-3">
                        <Badge tone={u.is_active ? "success" : "neutral"}>{u.is_active ? "Actif" : "Désactivé"}</Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        <Card>
          <CardHeader title="Équipes" />
          {!teams ? (
            <Spinner />
          ) : (
            <ul className="divide-y divide-line">
              {teams.map((t) => (
                <li key={t.id} className="flex items-center justify-between px-5 py-3">
                  <span>{t.name}</span>
                  <span className="text-muted">
                    {t.member_count} membre{t.member_count > 1 ? "s" : ""}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      {me.role === "ADMIN" && (
        <Card className="mt-6">
          <CardHeader title="Journal d'audit" description="20 dernières actions sensibles." />
          {!audit ? (
            <Spinner />
          ) : audit.length === 0 ? (
            <p className="px-5 py-6 text-muted">Aucune action enregistrée.</p>
          ) : (
            <ul className="divide-y divide-line">
              {audit.map((a) => (
                <li key={a.id} className="flex flex-wrap items-center gap-x-4 gap-y-1 px-5 py-2.5">
                  <span className="w-32 text-muted">{dateFmt.format(new Date(a.created_at))}</span>
                  <code className="rounded bg-canvas px-1.5 py-0.5 text-xs">{a.action}</code>
                  <span className="text-muted">{a.actor_email ?? "système"}</span>
                </li>
              ))}
            </ul>
          )}
        </Card>
      )}
    </>
  );
}
