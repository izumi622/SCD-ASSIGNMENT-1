import { useState, type FormEvent } from "react";
import type { ComplaintCreate, Complaint } from "../api/types";
import { useSubmitComplaint, useToasts } from "../hooks/useApi";
import ToastContainer from "../components/ToastContainer";

const CATEGORY_LABELS: Record<string, string> = {
  water: "Water Supply",
  electricity: "Electricity",
  sanitation: "Sanitation",
  roads: "Roads",
  streetlights: "Streetlights",
  other: "Other",
};

interface Props {
  onSubmitted: () => void;
}

export default function SubmitPage({ onSubmitted }: Props) {
  const [text, setText] = useState("");
  const [location, setLocation] = useState("");
  const [reporterContact, setReporterContact] = useState("");
  const { submit, loading } = useSubmitComplaint();
  const { toasts, addToast } = useToasts();
  const [result, setResult] = useState<Complaint | null>(null);

  const valid =
    text.trim().length >= 10 &&
    text.trim().length <= 2000 &&
    location.trim().length >= 3;

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!valid) return;

    const body: ComplaintCreate = {
      text: text.trim(),
      location: location.trim(),
    };
    if (reporterContact.trim()) {
      body.reporter_contact = reporterContact.trim();
    }

    const res = await submit(body);
    if (res) {
      setResult(res);
      addToast("Complaint submitted successfully!", "success");
      setText("");
      setLocation("");
      setReporterContact("");
      setTimeout(onSubmitted, 2500);
    } else {
      addToast("Failed to submit complaint", "error");
    }
  };

  return (
    <div style={{ maxWidth: 640, margin: "0 auto" }}>
      <div className="card">
        <h1 className="card-title">📝 Submit a Complaint</h1>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label" htmlFor="text">Complaint Description</label>
            <textarea
              id="text"
              className="form-textarea"
              placeholder="Describe the issue in detail (10 – 2,000 chars)"
              value={text}
              onChange={(e) => setText(e.target.value)}
              maxLength={2000}
              required
            />
            <p className="char-count">{text.length} / 2,000</p>
            {text.length > 0 && text.trim().length < 10 && (
              <p className="form-error">
                Text must be at least 10 characters
              </p>
            )}
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="location">Location</label>
            <input
              id="location"
              className="form-input"
              placeholder="e.g. 123 Main St, Downtown (min 3 chars)"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              maxLength={200}
              required
            />
            {location.length > 0 && location.trim().length < 3 && (
              <p className="form-error">Location must be at least 3 characters</p>
            )}
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="contact">Contact (optional)</label>
            <input
              id="contact"
              className="form-input"
              placeholder="Phone or email (optional)"
              value={reporterContact}
              onChange={(e) => setReporterContact(e.target.value)}
              maxLength={255}
            />
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            disabled={!valid || loading}
            style={{ width: "100%", marginTop: "0.5rem" }}
          >
            {loading ? "Submitting…" : "Submit Complaint"}
          </button>
        </form>

        {result && (
          <div className="triage-result">
            <h3>✨ AI Triage Result</h3>
            <div className="triage-detail">
              <div>
                <dt>Priority</dt>
                <dd>
                  <span className={`badge badge-${result.priority}`}>
                    {result.priority}
                  </span>
                </dd>
              </div>
              <div>
                <dt>Category</dt>
                <dd>
                  <span className="badge badge-category">
                    {CATEGORY_LABELS[result.category] ?? result.category}
                  </span>
                </dd>
              </div>
              <div>
                <dt>Triaged By</dt>
                <dd>{result.triaged_by}</dd>
              </div>
              <div>
                <dt>Latency</dt>
                <dd>{result.triage_latency_ms}ms</dd>
              </div>
              {result.ai_summary && (
                <div style={{ flexBasis: "100%" }}>
                  <dt>AI Summary</dt>
                  <dd>{result.ai_summary}</dd>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      <ToastContainer toasts={toasts} />
    </div>
  );
}
