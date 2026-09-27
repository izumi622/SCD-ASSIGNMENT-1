import { useState, useEffect, useCallback } from "react";
import { api, APIError } from "../api/client";
import type {
  Complaint,
  ComplaintCreate,
  PaginatedResponse,
  StatsResponse,
  Status,
} from "../api/types";

/* ─── Toast messages ─── */
export type ToastType = "success" | "error";
export interface Toast {
  id: number;
  message: string;
  type: ToastType;
}

let toastId = 0;

export function useToasts() {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const addToast = useCallback((message: string, type: ToastType = "success") => {
    const id = ++toastId;
    setToasts((t) => [...t, { id, message, type }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 4000);
  }, []);

  return { toasts, addToast };
}

/* ─── Fetch complaints ─── */
export function useComplaints(
  page: number,
  status?: string,
  priority?: string,
  category?: string,
) {
  const [data, setData] = useState<PaginatedResponse<Complaint> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.listComplaints({
        page,
        page_size: 10,
        status: status || undefined,
        priority: priority || undefined,
        category: category || undefined,
      });
      setData(res);
    } catch (e) {
      setError(e instanceof APIError ? e.message : "Failed to load complaints");
    } finally {
      setLoading(false);
    }
  }, [page, status, priority, category]);

  useEffect(() => { load(); }, [load]);

  return { data, loading, error, reload: load };
}

/* ─── Submit complaint ─── */
export function useSubmitComplaint() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = useCallback(async (body: ComplaintCreate) => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.createComplaint(body);
      return result;
    } catch (e) {
      const msg = e instanceof APIError ? e.message : "Submission failed";
      setError(msg);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  return { submit, loading, error };
}

/* ─── Patch status ─── */
export function usePatchStatus() {
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const patch = useCallback(
    async (id: string, newStatus: Status): Promise<{ data?: Complaint; error?: string }> => {
      setLoading(id);
      setError(null);
      try {
        const result = await api.updateComplaintStatus(id, newStatus);
        return { data: result };
      } catch (e) {
        const msg = e instanceof APIError ? e.message : (e instanceof Error ? e.message : "Update failed");
        setError(msg);
        return { error: msg };
      } finally {
        setLoading(null);
      }
    },
    [],
  );

  return { patch, loading, error };
}

/* ─── Stats ─── */
export function useStats() {
  const [data, setData] = useState<StatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getStats();
      setData({ ...res.data, cache_hit: res.cacheStatus === "HIT" });
    } catch (e) {
      setError(e instanceof APIError ? e.message : "Failed to load stats");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  return { data, loading, error, reload: load };
}
