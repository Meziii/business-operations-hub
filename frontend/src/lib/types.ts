// Contrats de l'API (backend/app/schemas.py). Génération automatique depuis l'OpenAPI prévue en phase 2.
export type Role = "ADMIN" | "MANAGER" | "AGENT" | "VIEWER";

export interface Team {
  id: string;
  code: string;
  name: string;
}

export interface TeamWithCount extends Team {
  member_count: number;
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: Role;
  is_active: boolean;
  teams: Team[];
}

export interface Me extends User {
  organization_name: string;
}

export interface AuditEntry {
  id: number;
  action: string;
  entity: string;
  entity_id: string | null;
  actor_email: string | null;
  details: Record<string, unknown>;
  created_at: string;
}

export interface Health {
  status: string;
  database: string;
  ai_provider: string;
}

export const ROLE_LABELS: Record<Role, string> = {
  ADMIN: "Administrateur",
  MANAGER: "Responsable",
  AGENT: "Collaborateur",
  VIEWER: "Lecture seule",
};
