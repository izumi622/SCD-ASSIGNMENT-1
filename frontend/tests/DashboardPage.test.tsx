import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import DashboardPage from "../src/pages/DashboardPage";
import { api } from "../src/api/client";
import type { PaginatedResponse, Complaint } from "../src/api/types";

vi.mock("../src/api/client", () => ({
  api: {
    listComplaints: vi.fn(),
    updateComplaintStatus: vi.fn(),
  },
  APIError: class extends Error {
    status: number;
    constructor(msg: string, status: number) {
      super(msg);
      this.status = status;
    }
  },
}));

describe("DashboardPage", () => {
  const mockComplaints: PaginatedResponse<Complaint> = {
    items: [
      {
        id: "c-101",
        text: "Main road pothole near school",
        location: "Blue Area, Sector F-6",
        reporter_contact: null,
        category: "roads",
        priority: "high",
        status: "open",
        ai_summary: "Dangerous pothole on main road",
        triaged_by: "rules",
        triage_latency_ms: 12,
        created_at: "2026-09-27T10:00:00Z",
        updated_at: "2026-09-27T10:00:00Z",
      },
    ],
    total: 1,
    page: 1,
    page_size: 10,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.listComplaints).mockResolvedValue(mockComplaints);
  });

  it("renders complaint list and filters", async () => {
    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("Main road pothole near school")).toBeInTheDocument();
      expect(screen.getByText(/Blue Area, Sector F-6/i)).toBeInTheDocument();
    });

    expect(screen.getByText("All Statuses")).toBeInTheDocument();
    expect(screen.getByText("All Priorities")).toBeInTheDocument();
  });

  it("allows status transitions according to state machine", async () => {
    vi.mocked(api.updateComplaintStatus).mockResolvedValueOnce({
      ...mockComplaints.items[0],
      status: "in_progress",
    });

    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("Main road pothole near school")).toBeInTheDocument();
    });

    // In open status, allowed transitions are "in_progress" and "rejected"
    const inProgressBtn = screen.getByRole("button", { name: /in progress/i });
    expect(inProgressBtn).toBeInTheDocument();

    fireEvent.click(inProgressBtn);

    await waitFor(() => {
      expect(api.updateComplaintStatus).toHaveBeenCalledWith("c-101", "in_progress");
    });
  });
});
