"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft, Sparkles } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { useSession } from "@/components/layout/session";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ErrorMessage, Spinner } from "@/components/ui/feedback";
import { Input, Label, Select, Textarea } from "@/components/ui/input";
import { api } from "@/lib/api";
import { CHANNEL_LABELS } from "@/lib/labels";
import type { Channel, ReferenceData, RequestDetail } from "@/lib/types";

export default function NewRequestPage() {
  const me = useSession();
  const router = useRouter();
  const [ref, setRef] = useState<ReferenceData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  useEffect(() => {
    api<ReferenceData>("/api/reference").then(setRef).catch((e: Error) => setError(e.message));
  }, []);

  if (me.role === "VIEWER") {
    return <ErrorMessage message="Votre rôle permet de consulter les demandes, pas d'en créer." />;
  }

  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    setPending(true);
    setError(null);
    try {
      const created = await api<RequestDetail>("/api/requests", {
        method: "POST",
        body: JSON.stringify({
          account_id: form.get("account_id"),
          channel: form.get("channel"),
          title: form.get("title"),
          description: form.get("description"),
        }),
      });
      router.push(`/requests/${created.id}`);
    } catch (err) {
      setError((err as Error).message);
      setPending(false);
    }
  }

  return (
    <>
      <Link href="/requests" className="mb-3 inline-flex items-center gap-1 text-muted hover:text-ink">
        <ArrowLeft className="size-4" aria-hidden /> Demandes
      </Link>
      <PageHeader title="Nouvelle demande" description="Saisissez la demande telle que le client l'a formulée." />
      {!ref ? (
        <Spinner />
      ) : (
        <Card className="max-w-2xl">
          <form onSubmit={submit} className="space-y-4 p-5">
            {error && <ErrorMessage message={error} />}
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <Label htmlFor="account_id">Client ou partenaire</Label>
                <Select id="account_id" name="account_id" required defaultValue="">
                  <option value="" disabled>
                    Choisir…
                  </option>
                  {ref.accounts.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.name}
                      {a.tier === "PREMIUM" ? " (Premium)" : ""}
                    </option>
                  ))}
                </Select>
              </div>
              <div>
                <Label htmlFor="channel">Canal</Label>
                <Select id="channel" name="channel" defaultValue="EMAIL">
                  {(Object.keys(CHANNEL_LABELS) as Channel[]).map((c) => (
                    <option key={c} value={c}>
                      {CHANNEL_LABELS[c]}
                    </option>
                  ))}
                </Select>
              </div>
            </div>
            <div>
              <Label htmlFor="title">Objet</Label>
              <Input id="title" name="title" required minLength={5} maxLength={200} placeholder="Ex. : Colis non reçu" />
            </div>
            <div>
              <Label htmlFor="description">Description</Label>
              <Textarea id="description" name="description" required minLength={10} rows={7} placeholder="Ce que demande le client, avec les références utiles." />
            </div>
            <p className="flex items-start gap-2 rounded-md bg-navy-50 px-3 py-2.5 text-navy-700">
              <Sparkles className="mt-0.5 size-4 shrink-0" aria-hidden />
              À l&apos;enregistrement, une catégorie, une priorité et une équipe vous seront proposées. Rien n&apos;est appliqué sans votre
              validation.
            </p>
            <div className="flex justify-end gap-2">
              <Link href="/requests">
                <Button type="button" variant="secondary">
                  Annuler
                </Button>
              </Link>
              <Button type="submit" disabled={pending}>
                {pending ? "Enregistrement…" : "Enregistrer la demande"}
              </Button>
            </div>
          </form>
        </Card>
      )}
    </>
  );
}
