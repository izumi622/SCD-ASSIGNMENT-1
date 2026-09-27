import { useStats } from "../hooks/useApi";

export default function StatsPage() {
  const { data, loading, error, reload } = useStats();

  if (loading) {
    return (
      <div className="loading-spinner">
        <div className="spinner" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="card" style={{ borderColor: "var(--danger)", maxWidth: 500, margin: "0 auto" }}>
        <p style={{ color: "var(--danger)" }}>{error}</p>
        <button className="btn btn-primary btn-sm" onClick={reload} style={{ marginTop: "0.5rem" }}>
          Retry
        </button>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "1.2rem" }}>
        <h1 className="card-title" style={{ margin: 0 }}>📊 Statistics</h1>
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <span className={`cache-indicator ${data.cache_hit ? "cache-hit" : "cache-miss"}`}>
            {data.cache_hit ? "⚡ Cache Hit" : "🔄 Fresh"}
          </span>
          <button className="btn btn-outline btn-sm" onClick={reload}>
            ↻ Refresh
          </button>
        </div>
      </div>

      {/* Summary stats */}
      <div className="stats-grid" style={{ marginBottom: "1.5rem" }}>
        <div className="stat-card">
          <div className="stat-value">{data.total_complaints}</div>
          <div className="stat-label">Total Complaints</div>
        </div>
      </div>

      {/* Breakdown cards */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "1rem" }}>
        <div className="card">
          <h2 className="card-title" style={{ fontSize: "0.95rem" }}>By Status</h2>
          {Object.entries(data.by_status).map(([k, v]) => (
            <div key={k} style={{ display: "flex", justifyContent: "space-between", padding: "0.35rem 0", borderBottom: "1px solid var(--border-color)" }}>
              <span className={`badge badge-${k}`}>{k}</span>
              <span style={{ fontWeight: 700, fontSize: "0.9rem" }}>{v}</span>
            </div>
          ))}
        </div>

        <div className="card">
          <h2 className="card-title" style={{ fontSize: "0.95rem" }}>By Priority</h2>
          {Object.entries(data.by_priority).map(([k, v]) => (
            <div key={k} style={{ display: "flex", justifyContent: "space-between", padding: "0.35rem 0", borderBottom: "1px solid var(--border-color)" }}>
              <span className={`badge badge-${k}`}>{k}</span>
              <span style={{ fontWeight: 700, fontSize: "0.9rem" }}>{v}</span>
            </div>
          ))}
        </div>

        <div className="card">
          <h2 className="card-title" style={{ fontSize: "0.95rem" }}>By Category</h2>
          {Object.entries(data.by_category).map(([k, v]) => (
            <div key={k} style={{ display: "flex", justifyContent: "space-between", padding: "0.35rem 0", borderBottom: "1px solid var(--border-color)" }}>
              <span className="badge badge-category">{k}</span>
              <span style={{ fontWeight: 700, fontSize: "0.9rem" }}>{v}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
