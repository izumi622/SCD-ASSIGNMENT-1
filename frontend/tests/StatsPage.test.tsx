import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import StatsPage from "../src/pages/StatsPage";
import { api } from "../src/api/client";

vi.mock("../src/api/client", () => ({
  api: {
    getStats: vi.fn(),
  },
  APIError: class extends Error {
    status: number;
    constructor(msg: string, status: number) {
      super(msg);
      this.status = status;
    }
  },
}));

describe("StatsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders statistics and cache hit badge", async () => {
    vi.mocked(api.getStats).mockResolvedValueOnce({
      data: {
        total_complaints: 42,
        by_status: { open: 20, in_progress: 10, resolved: 10, rejected: 2 },
        by_priority: { high: 15, normal: 20, low: 7 },
        by_category: { water: 12, electricity: 10, sanitation: 8, roads: 6, streetlights: 4, other: 2 },
        cache_hit: true,
      },
      cacheStatus: "HIT",
    });

    render(<StatsPage />);

    await waitFor(() => {
      expect(screen.getByText("42")).toBeInTheDocument();
      expect(screen.getByText(/total complaints/i)).toBeInTheDocument();
      expect(screen.getByText(/⚡ Cache Hit/i)).toBeInTheDocument();
      expect(screen.getByText(/by status/i)).toBeInTheDocument();
      expect(screen.getByText(/by priority/i)).toBeInTheDocument();
      expect(screen.getByText(/by category/i)).toBeInTheDocument();
    });
  });

  it("renders fresh state when cache is MISS", async () => {
    vi.mocked(api.getStats).mockResolvedValueOnce({
      data: {
        total_complaints: 10,
        by_status: { open: 10 },
        by_priority: { normal: 10 },
        by_category: { water: 10 },
        cache_hit: false,
      },
      cacheStatus: "MISS",
    });

    render(<StatsPage />);

    await waitFor(() => {
      expect(screen.getByText(/🔄 Fresh/i)).toBeInTheDocument();
    });
  });
});
