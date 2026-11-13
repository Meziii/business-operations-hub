// Contrats de l'API (schémas Pydantic du backend), écrits à la main. Génération depuis l'OpenAPI : voir le bilan de phase 2.
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

// --- Module 1 : demandes (backend/app/modules/requests/schemas.py) ---
export type Status = "NEW" | "CLASSIFIED" | "ASSIGNED" | "IN_PROGRESS" | "WAITING_INFO" | "RESOLVED" | "CLOSED";
export type Priority = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type Channel = "EMAIL" | "PHONE" | "PORTAL" | "PARTNER";
export type SlaState = "NONE" | "ON_TRACK" | "AT_RISK" | "BREACHED" | "MET";
export type Decision = "PENDING" | "ACCEPTED" | "MODIFIED" | "REJECTED";

export interface Ref {
  id: string;
  name: string;
}

export interface UserRef {
  id: string;
  full_name: string;
}

export interface Account {
  id: string;
  name: string;
  type: "CUSTOMER" | "PARTNER";
  tier: "STANDARD" | "PREMIUM";
}

export interface Category {
  id: string;
  code: string;
  name: string;
  description: string;
  default_team_id: string | null;
}

export interface SlaPolicy {
  priority: Priority;
  response_minutes: number;
  resolution_minutes: number;
}

export interface ReferenceData {
  accounts: Account[];
  categories: Category[];
  teams: Team[];
  sla: SlaPolicy[];
  assignees: { id: string; full_name: string; team_ids: string[] }[];
  ai_provider: string;
}

export interface RequestRow {
  id: string;
  reference: string;
  title: string;
  status: Status;
  priority: Priority | null;
  channel: Channel;
  account: Ref;
  category: Ref | null;
  team: Team | null;
  assignee: UserRef | null;
  created_at: string;
  due_response_at: string | null;
  due_resolution_at: string | null;
  sla_state: SlaState;
  sla_next_due: string | null;
}

export interface RequestPage {
  items: RequestRow[];
  total: number;
  page: number;
  page_size: number;
}

export interface RequestEvent {
  id: number;
  event_type: string;
  field: string | null;
  old_value: string | null;
  new_value: string | null;
  actor: UserRef | null;
  created_at: string;
}

export interface Comment {
  id: string;
  body: string;
  author: UserRef | null;
  created_at: string;
}

export interface Attachment {
  id: string;
  filename: string;
  mime_type: string;
  size_bytes: number;
  sha256: string;
  uploaded_by: UserRef | null;
  created_at: string;
}

export interface Suggestion {
  id: string;
  proposal: {
    category_id: string;
    category_code: string;
    priority: Priority;
    team_id: string;
    team_code: string;
    field_confidence: Record<"category" | "priority" | "team", number>;
  };
  explanation: string;
  confidence: number;
  provider: string;
  latency_ms: number;
  decision: Decision;
  final_value: Record<string, string> | null;
  decided_by: UserRef | null;
  decided_at: string | null;
  created_at: string;
}

export interface RequestDetail extends RequestRow {
  description: string;
  account_tier: "STANDARD" | "PREMIUM";
  created_by: UserRef | null;
  first_response_at: string | null;
  resolved_at: string | null;
  closed_at: string | null;
  updated_at: string;
  can_edit: boolean;
  allowed_transitions: Status[];
  comments: Comment[];
  attachments: Attachment[];
  events: RequestEvent[];
  suggestion: Suggestion | null;
  documents: LinkedDocument[];
}

export interface RequestStats {
  open: number;
  overdue: number;
  to_classify: number;
  waiting_info: number;
  resolved_last_7_days: number;
  by_status: Record<Status, number>;
  by_team: { team: Team; open: number; overdue: number; unassigned: number }[];
  ai_decisions: Record<Decision, number>;
}

export interface FieldScore {
  field: "category" | "priority" | "team";
  correct: number;
  total: number;
  accuracy: number;
}

// --- Module 2 : documents ---------------------------------------------------------------

export type DocType = "INVOICE" | "WARRANTY_CLAIM";
export type DocStatus = "TO_REVIEW" | "VALIDATED" | "REJECTED";

export interface DocumentRow {
  id: string;
  reference: string;
  doc_type: DocType;
  status: DocStatus;
  filename: string;
  summary: string;
  amount: number | null;
  blocking: number;
  warnings: number;
  ocr_used: boolean;
  request: { id: string; reference: string; title: string } | null;
  uploaded_by: UserRef | null;
  created_at: string;
}

export interface DocumentPage {
  items: DocumentRow[];
  total: number;
  page: number;
  page_size: number;
}

export interface ExtractedField {
  name: string;
  label: string;
  kind: "text" | "date" | "amount";
  required: boolean;
  value: string | number | null;
  proposed: string | number | null;
  confidence: number;
  corrected: boolean;
}

export interface DocAnomaly {
  code: string;
  severity: "BLOCKING" | "WARNING";
  field: string | null;
  message: string;
}

export interface DocVersion {
  version: number;
  source: "AI" | "HUMAN";
  provider: string;
  created_at: string;
  created_by: UserRef | null;
  changed: string[];
}

export interface DocumentDetail extends DocumentRow {
  size_bytes: number;
  page_count: number;
  ocr_pages: number;
  ocr_confidence: number | null;
  text: string;
  text_error: string | null;
  provider: string;
  fields: ExtractedField[];
  anomalies: DocAnomaly[];
  versions: DocVersion[];
  decision: Decision | null;
  decided_by: UserRef | null;
  decided_at: string | null;
  rejection_reason: string | null;
  can_edit: boolean;
}

export interface DocumentStats {
  to_review: number;
  with_blocking: number;
  validated: number;
  rejected: number;
}

export interface LinkedDocument {
  id: string;
  reference: string;
  doc_type: DocType;
  status: DocStatus;
  filename: string;
}

export interface DocFieldScore {
  field: string;
  label: string;
  correct: number;
  total: number;
  accuracy: number;
}

export interface DocQuality {
  dev_documents_fully_correct: number;
  offline: {
    provider: string;
    split: string;
    size: number;
    evaluated: number;
    skipped_scans: number;
    fields: DocFieldScore[];
    documents_fully_correct: number;
    text_accuracy: number | null;
    scan_accuracy: number | null;
    by_layout: Record<string, number>;
    anomalies: { expected: number; detected: number; false_alarms: number };
    errors: Record<string, string>[];
  };
  live: {
    decided: number;
    accepted: number;
    modified: number;
    rejected: number;
    field_kept: Record<string, number>;
  };
}

export interface Quality {
  dev_all_three_correct: number;
  offline: {
    provider: string;
    dataset: string;
    split: string;
    size: number;
    fields: FieldScore[];
    all_three_correct: number;
    mean_latency_ms: number;
    category_confusion: { expected: string; predicted: string; count: number }[];
    errors: Record<string, string>[];
  };
  live: {
    decided: number;
    accepted: number;
    modified: number;
    rejected: number;
    field_kept: Record<"category_id" | "priority" | "team_id", number>;
  };
}
