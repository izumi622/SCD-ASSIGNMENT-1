/* ─── Enums ─── */
export type Category = "water" | "electricity" | "sanitation" | "roads" | "streetlights" | "other";
export type Priority = "high" | "normal" | "low";
export type Status = "open" | "in_progress" | "resolved" | "rejected";

/* ─── Complaint ─── */
export interface Complaint {
  id: string;
  text: string;
  location: string;
  reporter_contact?: string | null;
  category: Category;
  priority: Priority;
  status: Status;
  ai_summary?: string | null;
  triaged_by: string;
  triage_latency_ms: number;
  created_at: string;
  updated_at: string;
}

export interface ComplaintCreate {
  text: string;
  location: string;
  reporter_contact?: string;
}

/* ─── List Response ─── */
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

/* ─── Stats ─── */
export interface StatsResponse {
  total_complaints: number;
  by_category: Record<string, number>;
  by_priority: Record<string, number>;
  by_status: Record<string, number>;
  cache_hit: boolean; // derived from X-Cache header
}

/* ─── Triage Meta ─── */
export interface TriageOutcome {
  provider: string;
  latency_ms: number;
  fallback: boolean;
  timestamp: string;
}

export interface ProvidersMetaResponse {
  active_provider: string;
  recent_outcomes: TriageOutcome[];
}

/* ─── Errors ─── */
export interface APIErrorDetail {
  loc: string[];
  msg: string;
  type: string;
}

export interface APIErrorResponse {
  detail: string | APIErrorDetail[];
}
