"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LogOut } from "lucide-react";
import { api } from "@/lib/api";
import { ROLE_LABELS } from "@/lib/types";
import { cn } from "@/lib/utils";
import { NAV } from "./nav";
import { useSession } from "./session";

export function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const me = useSession();
  const items = NAV.filter((i) => !i.roles || i.roles.includes(me.role));

  async function logout() {
    await api("/api/auth/logout", { method: "POST" });
    window.location.href = "/login";
  }

  return (
    <aside className="flex h-full w-60 flex-col bg-navy-900 text-navy-100">
      <div className="px-5 pt-5 pb-6">
        <p className="font-semibold tracking-tight text-white">Operations Hub</p>
        <p className="mt-0.5 text-xs text-navy-200/80">{me.organization_name}</p>
      </div>
      <nav aria-label="Navigation principale" className="flex-1 space-y-0.5 px-3">
        {items.map(({ href, label, icon: Icon }) => {
          const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              onClick={onNavigate}
              aria-current={active ? "page" : undefined}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 transition-colors",
                active ? "bg-navy-700 text-white" : "hover:bg-navy-800 hover:text-white",
              )}
            >
              <Icon className="size-4" aria-hidden />
              {label}
            </Link>
          );
        })}
      </nav>
      <div className="border-t border-navy-800 px-5 py-4">
        <p className="truncate font-medium text-white">{me.full_name}</p>
        <p className="text-xs text-navy-200/80">{ROLE_LABELS[me.role]}</p>
        <button onClick={logout} className="mt-3 flex items-center gap-2 text-xs text-navy-200 hover:text-white">
          <LogOut className="size-3.5" aria-hidden /> Se déconnecter
        </button>
      </div>
    </aside>
  );
}
