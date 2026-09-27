import { useState, useCallback } from "react";
import SubmitPage from "./pages/SubmitPage";
import DashboardPage from "./pages/DashboardPage";
import StatsPage from "./pages/StatsPage";

type Tab = "submit" | "dashboard" | "stats";

export default function App() {
  const [tab, setTab] = useState<Tab>("dashboard");
  const [refreshKey, setRefreshKey] = useState(0);

  const onSubmitted = useCallback(() => {
    setRefreshKey((k) => k + 1);
    setTab("dashboard");
  }, []);

  return (
    <>
      <header className="app-header">
        <div className="app-logo">
          <span className="dot" />
          CivicPulse
        </div>
        <nav className="nav-tabs">
          <button
            className={`nav-tab ${tab === "dashboard" ? "active" : ""}`}
            onClick={() => setTab("dashboard")}
          >
            Dashboard
          </button>
          <button
            className={`nav-tab ${tab === "submit" ? "active" : ""}`}
            onClick={() => setTab("submit")}
          >
            Submit
          </button>
          <button
            className={`nav-tab ${tab === "stats" ? "active" : ""}`}
            onClick={() => setTab("stats")}
          >
            Stats
          </button>
        </nav>
      </header>

      <main className="app-content">
        {tab === "dashboard" && <DashboardPage key={refreshKey} />}
        {tab === "submit" && <SubmitPage onSubmitted={onSubmitted} />}
        {tab === "stats" && <StatsPage />}
      </main>
    </>
  );
}
