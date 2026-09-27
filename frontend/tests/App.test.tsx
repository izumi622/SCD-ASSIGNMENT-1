import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import App from "../src/App";

vi.mock("../src/api/client", () => ({
  api: {
    listComplaints: vi.fn().mockResolvedValue({ items: [], total: 0, page: 1, page_size: 10 }),
    getStats: vi.fn().mockResolvedValue({
      data: {
        total_complaints: 0,
        by_status: {},
        by_priority: {},
        by_category: {},
      },
      cacheStatus: "HIT",
    }),
    createComplaint: vi.fn(),
  },
  APIError: class extends Error {},
}));

describe("App", () => {
  it("renders header and navigates between tabs", async () => {
    render(<App />);

    expect(screen.getByText("CivicPulse")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Dashboard" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Submit" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Stats" })).toBeInTheDocument();

    // Default tab is Dashboard
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Dashboard" })).toHaveClass("active");
    });

    // Switch to Submit
    fireEvent.click(screen.getByRole("button", { name: "Submit" }));
    expect(screen.getByRole("button", { name: "Submit" })).toHaveClass("active");
    expect(screen.getByLabelText(/complaint description/i)).toBeInTheDocument();

    // Switch to Stats
    fireEvent.click(screen.getByRole("button", { name: "Stats" }));
    expect(screen.getByRole("button", { name: "Stats" })).toHaveClass("active");
    await waitFor(() => {
      expect(screen.getByText(/total complaints/i)).toBeInTheDocument();
    });
  });
});
