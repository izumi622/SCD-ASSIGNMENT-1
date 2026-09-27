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

/* Allowed status transitions (matches backend state machine) */
const TRANSITIONS: Record<string, Status[]> = {
  open: ["in_progress", "rejected"],
  in_progress: ["resolved", "rejected"],
  resolved: [],
  rejected: [],
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

  const { data, loading, error, reload } = useComplaints(
    page,
    statusFilter || undefined,
    priorityFilter || undefined,
  );

  const { patch, loading: patching } = usePatchStatus();
  const { toasts, addToast } = useToasts();

  const totalPages = data ? Math.ceil(data.total / data.page_size) : 1;

  const handleStatusChange = useCallback(
    async (id: string, newStatus: Status) => {
      const result = await patch(id, newStatus);
      if (result) {
        addToast(`Status updated to ${STATUS_LABELS[newStatus]}`, "success");
        reload();
      } else {
        addToast("Failed to update status", "error");
      }
    },
    [patch, addToast, reload],
  );

  const formatDate = (iso: string) =>
    new Date(iso).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });

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
              <div key={c.id} className="complaint-row">
                <div>
                  <div className="complaint-text">
                    {c.text.length > 200
                      ? c.text.slice(0, 200) + "…"
                      : c.text}
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
                  {(TRANSITIONS[c.status] ?? []).map((next) => (
                    <button
                      key={next}
                      className={`status-btn to-${next}`}
                      disabled={patching === c.id}
                      onClick={() => handleStatusChange(c.id, next)}
                    >
                      → {STATUS_LABELS[next]}
                    </button>
                  ))}
                </div>
              </div>
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
