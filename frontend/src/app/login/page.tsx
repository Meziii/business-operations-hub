"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { ErrorMessage } from "@/components/ui/feedback";
import { Input, Label } from "@/components/ui/input";
import { api } from "@/lib/api";

export default function LoginPage() {
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    setPending(true);
    setError(null);
    try {
      await api("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ email: form.get("email"), password: form.get("password") }),
      });
      window.location.href = "/";
    } catch (err) {
      setError(err instanceof Error ? err.message : "Connexion impossible.");
      setPending(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <p className="text-lg font-semibold tracking-tight text-navy-900">Business Operations Hub</p>
          <p className="mt-1 text-muted">Demandes, documents, connaissance et pilotage</p>
        </div>
        <form onSubmit={onSubmit} className="space-y-4 rounded-[var(--radius-card)] border border-line bg-surface p-6">
          <div>
            <Label htmlFor="email">E-mail professionnel</Label>
            <Input id="email" name="email" type="email" autoComplete="username" required />
          </div>
          <div>
            <Label htmlFor="password">Mot de passe</Label>
            <Input id="password" name="password" type="password" autoComplete="current-password" required />
          </div>
          {error && <ErrorMessage message={error} />}
          <Button type="submit" className="w-full" disabled={pending}>
            {pending ? "Connexion…" : "Se connecter"}
          </Button>
        </form>
        <p className="mt-6 text-center text-xs text-muted">
          Environnement de démonstration. Toutes les données sont synthétiques.
        </p>
      </div>
    </main>
  );
}
