import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import DashboardPage from "../src/pages/DashboardPage";
import { api, APIError } from "../src/api/client";
import type { PaginatedResponse, Complaint } from "../src/api/types";

vi.mock("../src/api/client", () => {
  class MockAPIError extends Error {
    status: number;
    data: any;
    constructor(message: string, status: number, data?: any) {
      super(message);
      this.name = "APIError";
      this.status = status;
      this.data = data;
    }
  }

  return {
    api: {
      listComplaints: vi.fn(),
      updateComplaintStatus: vi.fn(),
    },
    APIError: MockAPIError,
  };
});

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

  it("renders complaint list and all filters including category", async () => {
    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("Main road pothole near school")).toBeInTheDocument();
      expect(screen.getByText(/Blue Area, Sector F-6/i)).toBeInTheDocument();
    });

    expect(screen.getByText("All Statuses")).toBeInTheDocument();
    expect(screen.getByText("All Priorities")).toBeInTheDocument();
    expect(screen.getByText("All Categories")).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Roads" })).toBeInTheDocument();
  });

  it("filters complaints when category dropdown changes", async () => {
    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("Main road pothole near school")).toBeInTheDocument();
    });

    // Find the category dropdown (the select containing 'All Categories')
    const categorySelect = screen.getByDisplayValue("All Categories");
    fireEvent.change(categorySelect, { target: { value: "roads" } });

    await waitFor(() => {
      expect(api.listComplaints).toHaveBeenCalledWith(
        expect.objectContaining({
          category: "roads",
        }),
      );
    });
  });

  it("allows selecting a new status from the status dropdown", async () => {
    vi.mocked(api.updateComplaintStatus).mockResolvedValueOnce({
      ...mockComplaints.items[0],
      status: "in_progress",
    });

    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("Main road pothole near school")).toBeInTheDocument();
    });

    // The status transition select dropdown
    const statusSelect = screen.getByDisplayValue("Change status…");
    expect(statusSelect).toBeInTheDocument();

    fireEvent.change(statusSelect, { target: { value: "in_progress" } });

    await waitFor(() => {
      expect(api.updateComplaintStatus).toHaveBeenCalledWith("c-101", "in_progress");
    });
  });

  it("displays the server's exact 409 error message when transition is rejected", async () => {
    const server409Message = "Invalid transition from open to resolved";
    vi.mocked(api.updateComplaintStatus).mockRejectedValueOnce(
      new APIError(server409Message, 409, { detail: server409Message }),
    );

    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText("Main road pothole near school")).toBeInTheDocument();
    });

    const statusSelect = screen.getByDisplayValue("Change status…");
    fireEvent.change(statusSelect, { target: { value: "resolved" } });

    await waitFor(() => {
      // The toast must display the exact message returned by the server
      expect(screen.getByText(server409Message)).toBeInTheDocument();
    });
  });
});
