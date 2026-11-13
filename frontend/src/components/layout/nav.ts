import { BarChart3, Bot, FileText, Inbox, LayoutDashboard, Settings, type LucideIcon } from "lucide-react";
import type { Role } from "@/lib/types";

export interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  roles?: Role[];
}

export const NAV: NavItem[] = [
  { href: "/", label: "Vue d'ensemble", icon: LayoutDashboard },
  { href: "/requests", label: "Demandes", icon: Inbox },
  { href: "/documents", label: "Documents", icon: FileText },
  { href: "/assistant", label: "Assistant", icon: Bot },
  { href: "/analytics", label: "Pilotage", icon: BarChart3 },
  { href: "/admin", label: "Administration", icon: Settings, roles: ["ADMIN", "MANAGER"] },
];
