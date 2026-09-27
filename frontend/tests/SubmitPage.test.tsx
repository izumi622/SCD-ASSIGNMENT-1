import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import SubmitPage from "../src/pages/SubmitPage";
import { api } from "../src/api/client";
import type { Complaint } from "../src/api/types";

vi.mock("../src/api/client", () => ({
  api: {
    createComplaint: vi.fn(),
  },
  APIError: class extends Error {
    status: number;
    constructor(msg: string, status: number) {
      super(msg);
      this.status = status;
    }
  },
}));

describe("SubmitPage", () => {
  const onSubmittedMock = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the submission form with required fields", () => {
    render(<SubmitPage onSubmitted={onSubmittedMock} />);
    expect(screen.getByLabelText(/complaint description/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/location/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/contact/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /submit complaint/i })).toBeInTheDocument();
  });

  it("shows validation error when complaint text is under 10 characters", () => {
    render(<SubmitPage onSubmitted={onSubmittedMock} />);
    const textarea = screen.getByLabelText(/complaint description/i);
    fireEvent.change(textarea, { target: { value: "Short" } });

    expect(screen.getByText(/text must be at least 10 characters/i)).toBeInTheDocument();
  });

  it("submits valid complaint and displays triage result", async () => {
    const mockComplaint: Complaint = {
      id: "123e4567-e89b-12d3-a456-426614174000",
      text: "Water pipeline burst causing severe flooding on main street",
      location: "Sector G-9 Islamabad",
      reporter_contact: "citizen@example.com",
      category: "water",
      priority: "high",
      status: "open",
      ai_summary: "Severe water pipeline burst and street flooding in G-9",
      triaged_by: "llm:groq",
      triage_latency_ms: 342,
      created_at: "2026-09-27T10:00:00Z",
      updated_at: "2026-09-27T10:00:00Z",
    };

    vi.mocked(api.createComplaint).mockResolvedValueOnce(mockComplaint);

    render(<SubmitPage onSubmitted={onSubmittedMock} />);

    fireEvent.change(screen.getByLabelText(/complaint description/i), {
      target: { value: "Water pipeline burst causing severe flooding on main street" },
    });
    fireEvent.change(screen.getByLabelText(/location/i), {
      target: { value: "Sector G-9 Islamabad" },
    });
    fireEvent.click(screen.getByRole("button", { name: /submit complaint/i }));

    await waitFor(() => {
      expect(api.createComplaint).toHaveBeenCalledWith({
        text: "Water pipeline burst causing severe flooding on main street",
        location: "Sector G-9 Islamabad",
      });
    });

    await waitFor(() => {
      expect(screen.getByText(/triage result/i)).toBeInTheDocument();
      expect(screen.getByText(/llm:groq/i)).toBeInTheDocument();
    });
  });
});
