import { useState, useCallback } from "react";
import { useComplaints, usePatchStatus, useToasts } from "../hooks/useApi";
import ToastContainer from "../components/ToastContainer";
import type { Complaint, Status } from "../api/types";

const STATUS_LABELS: Record<string, string> = {
  open: "Open",
  in_progress: "In Progress",
  resolved: "Resolved",
  rejected: "Rejected",
};

const PRIORITY_LABELS: Record<string, string> = {
  high: "High",
  normal: "Normal",
  low: "Low",
};

const CATEGORY_LABELS: Record<string, string> = {
  water: "Water",
  electricity: "Electricity",
  sanitation: "Sanitation",
  roads: "Roads",
  streetlights: "Streetlights",
  other: "Other",
};

export default function DashboardPage() {
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");

  const { data, loading, error, reload } = useComplaints(
    page,
    statusFilter || undefined,
    priorityFilter || undefined,
    categoryFilter || undefined,
  );

  const { patch, loading: patching } = usePatchStatus();
  const { toasts, addToast } = useToasts();

  const totalPages = data ? Math.ceil(data.total / data.page_size) : 1;

  /**
   * Wraps status change to surface server-side error messages (including 409)
   * directly in a toast notification.
   */
  const handleStatusChangeWithToast = useCallback(
    async (id: string, newStatus: Status) => {
      try {
        const result = await patch(id, newStatus);
        if (result) {
          addToast(`Status updated to ${STATUS_LABELS[newStatus]}`, "success");
          reload();
        }
      } catch {
        // Swallowed — usePatchStatus already sets error state
      }
    },
    [patch, addToast, reload],
  );

  return (
    <div>
      <h1 className="card-title" style={{ marginBottom: "1rem" }}>
        📋 Complaint Dashboard
      </h1>

      {/* Filters */}
      <div className="filters-bar">
        <select
          className="form-select"
          style={{ width: "auto", minWidth: 160 }}
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
        >
          <option value="">All Statuses</option>
          {Object.entries(STATUS_LABELS).map(([v, l]) => (
            <option key={v} value={v}>{l}</option>
          ))}
        </select>

        <select
          className="form-select"
          style={{ width: "auto", minWidth: 160 }}
          value={priorityFilter}
          onChange={(e) => { setPriorityFilter(e.target.value); setPage(1); }}
        >
          <option value="">All Priorities</option>
          {Object.entries(PRIORITY_LABELS).map(([v, l]) => (
            <option key={v} value={v}>{l}</option>
          ))}
        </select>

        <select
          className="form-select"
          style={{ width: "auto", minWidth: 160 }}
          value={categoryFilter}
          onChange={(e) => { setCategoryFilter(e.target.value); setPage(1); }}
        >
          <option value="">All Categories</option>
          {Object.entries(CATEGORY_LABELS).map(([v, l]) => (
            <option key={v} value={v}>{l}</option>
          ))}
        </select>

        <button className="btn btn-outline" onClick={() => reload()}>
          ↻ Refresh
        </button>

        {data && (
          <span style={{ marginLeft: "auto", fontSize: "0.8rem", color: "var(--text-muted)" }}>
            {data.total} total complaint{data.total !== 1 ? "s" : ""}
          </span>
        )}
      </div>

      {/* Loading */}
      {loading && (
        <div className="loading-spinner">
          <div className="spinner" />
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="card" style={{ borderColor: "var(--danger)" }}>
          <p style={{ color: "var(--danger)" }}>{error}</p>
          <button className="btn btn-primary btn-sm" onClick={reload} style={{ marginTop: "0.5rem" }}>
            Retry
          </button>
        </div>
      )}

      {/* Complaint list */}
      {!loading && data && (
        <>
          <div className="complaint-list">
            {data.items.length === 0 && (
              <div className="card" style={{ textAlign: "center", padding: "2rem" }}>
                <p style={{ color: "var(--text-muted)" }}>No complaints found</p>
              </div>
            )}

            {data.items.map((c: Complaint) => (
              <ComplaintCard
                key={c.id}
                complaint={c}
                patching={patching}
                onStatusChange={handleStatusChangeWithToast}
                addToast={addToast}
                patch={patch}
                reload={reload}
              />
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="pagination">
              <button
                className="btn btn-outline btn-sm"
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
              >
                ← Prev
              </button>
              <span style={{ fontSize: "0.82rem", color: "var(--text-secondary)" }}>
                Page {page} of {totalPages}
              </span>
              <button
                className="btn btn-outline btn-sm"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
              >
                Next →
              </button>
            </div>
          )}
        </>
      )}

      <ToastContainer toasts={toasts} />
    </div>
  );
}

/* ── ComplaintCard ──────────────────────────────────────── */

/**
 * Server-driven status actions: the backend returns 409 with a message
 * naming the invalid transition. We display that message as a toast
 * rather than hardcoding a client-side transition table.
 */
function ComplaintCard({
  complaint: c,
  patching,
  addToast,
  patch,
  reload,
}: {
  complaint: Complaint;
  patching: string | null;
  onStatusChange: (id: string, s: Status) => Promise<void>;
  addToast: (msg: string, type: "success" | "error") => void;
  patch: (id: string, s: Status) => Promise<{ data?: Complaint; error?: string }>;
  reload: () => void;
}) {
  /** All possible next statuses. The server enforces validity. */
  const allStatuses: Status[] = ["open", "in_progress", "resolved", "rejected"];
  const availableTransitions = allStatuses.filter((s) => s !== c.status);

  const handleChange = async (newStatus: Status) => {
    const result = await patch(c.id, newStatus);
    if (result.data) {
      addToast(`Status updated to ${STATUS_LABELS[newStatus]}`, "success");
      reload();
    } else if (result.error) {
      // Display the server's exact 409 error message (e.g. "Invalid transition from in_progress to open")
      addToast(result.error, "error");
    } else {
      addToast(`Cannot transition to ${STATUS_LABELS[newStatus]}`, "error");
    }
  };

  const formatDate = (iso: string) =>
    new Date(iso).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });

  return (
    <div className="complaint-row">
      <div>
        <div className="complaint-text">
          {c.text.length > 200 ? c.text.slice(0, 200) + "…" : c.text}
        </div>
        {c.ai_summary && (
          <div className="complaint-summary">💡 {c.ai_summary}</div>
        )}
        <div className="complaint-meta">
          📍 {c.location} · {formatDate(c.created_at)}
          {c.triaged_by && <> · 🤖 {c.triaged_by}</>}
        </div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "0.3rem", alignItems: "flex-end" }}>
        <span className={`badge badge-${c.priority}`}>
          {PRIORITY_LABELS[c.priority] ?? c.priority}
        </span>
        <span className="badge badge-category">
          {CATEGORY_LABELS[c.category] ?? c.category}
        </span>
      </div>

      <div>
        <span className={`badge badge-${c.status}`}>
          {STATUS_LABELS[c.status] ?? c.status}
        </span>
      </div>

      <div className="status-actions">
        {availableTransitions.length > 0 ? (
          <select
            className="form-select form-select-sm"
            disabled={patching === c.id}
            value=""
            onChange={(e) => {
              if (e.target.value) handleChange(e.target.value as Status);
            }}
          >
            <option value="">Change status…</option>
            {availableTransitions.map((next) => (
              <option key={next} value={next}>
                → {STATUS_LABELS[next]}
              </option>
            ))}
          </select>
        ) : (
          <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Terminal</span>
        )}
      </div>
    </div>
  );
}
