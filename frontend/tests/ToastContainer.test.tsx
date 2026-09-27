import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import ToastContainer from "../src/components/ToastContainer";
import type { Toast } from "../src/hooks/useApi";

describe("ToastContainer", () => {
  it("renders nothing when toasts array is empty", () => {
    const { container } = render(<ToastContainer toasts={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders multiple toasts with appropriate classes", () => {
    const toasts: Toast[] = [
      { id: 1, message: "Complaint created successfully", type: "success" },
      { id: 2, message: "Network connection error", type: "error" },
    ];

    render(<ToastContainer toasts={toasts} />);

    expect(screen.getByText("Complaint created successfully")).toBeInTheDocument();
    expect(screen.getByText("Network connection error")).toBeInTheDocument();
  });
});
