"use client";

import { useEffect, useState } from "react";
import { Menu, X } from "lucide-react";
import { SessionContext } from "@/components/layout/session";
import { Sidebar } from "@/components/layout/sidebar";
import { Spinner } from "@/components/ui/feedback";
import { api } from "@/lib/api";
import type { Me } from "@/lib/types";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const [me, setMe] = useState<Me | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    api<Me>("/api/auth/me").then(setMe).catch(() => undefined); // 401 → redirection gérée par api()
  }, []);

  if (!me) return <Spinner label="Ouverture de votre espace…" />;

  return (
    <SessionContext.Provider value={me}>
      <div className="flex min-h-screen">
        <div className="sticky top-0 hidden h-screen lg:block">
          <Sidebar />
        </div>
        {menuOpen && (
          <div className="fixed inset-0 z-40 flex lg:hidden">
            <Sidebar onNavigate={() => setMenuOpen(false)} />
            <button aria-label="Fermer le menu" className="flex-1 bg-ink/30" onClick={() => setMenuOpen(false)}>
              <X className="ml-auto mr-4 mt-4 size-5 text-white" aria-hidden />
            </button>
          </div>
        )}
        <div className="min-w-0 flex-1">
          <header className="flex h-14 items-center border-b border-line bg-surface px-4 lg:hidden">
            <button aria-label="Ouvrir le menu" onClick={() => setMenuOpen(true)} className="p-1">
              <Menu className="size-5" aria-hidden />
            </button>
            <span className="ml-3 font-semibold">Operations Hub</span>
          </header>
          <main className="mx-auto max-w-6xl px-4 py-6 lg:px-8 lg:py-8">{children}</main>
        </div>
      </div>
    </SessionContext.Provider>
  );
}
