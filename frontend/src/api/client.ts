import {
  Complaint,
  ComplaintCreate,
  PaginatedResponse,
  ProvidersMetaResponse,
  StatsResponse,
  Status,
} from './types';

/** Combined stats + cache status result */
export interface StatsWithCache {
  data: StatsResponse;
  cacheStatus: 'HIT' | 'MISS' | 'UNKNOWN';
}

type ComplaintListResponse = PaginatedResponse<Complaint>;

export class APIError extends Error {
  status: number;
  data: any;

  constructor(message: string, status: number, data?: any) {
    super(message);
    this.name = 'APIError';
    this.status = status;
    this.data = data;
  }
}

// Runtime configuration resolution (§2.1): Reads from /config.js if present, falls back to relative /api
function getBaseUrl(): string {
  if (typeof window !== 'undefined' && (window as any).__CIVICPULSE_CONFIG__?.API_BASE_URL) {
    return (window as any).__CIVICPULSE_CONFIG__.API_BASE_URL.replace(/\/$/, '');
  }
  return '/api';
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<{ data: T; headers: Headers }> {
  const baseUrl = getBaseUrl();
  const url = `${baseUrl}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;

  const defaultHeaders: HeadersInit = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  };

  const response = await fetch(url, {
    ...options,
    headers: {
      ...defaultHeaders,
      ...options.headers,
    },
  });

  if (!response.ok) {
    let errorMessage = `HTTP Error ${response.status}: ${response.statusText}`;
    let errorData = null;

    try {
      errorData = await response.json();
      if (typeof errorData?.detail === 'string') {
        errorMessage = errorData.detail;
      } else if (Array.isArray(errorData?.detail)) {
        errorMessage = errorData.detail.map((d: any) => `${d.loc?.join('.') || 'field'}: ${d.msg}`).join(', ');
      }
    } catch {
      // Keep fallback message
    }

    throw new APIError(errorMessage, response.status, errorData);
  }

  const data = (await response.json()) as T;
  return { data, headers: response.headers };
}

export const api = {
  async createComplaint(payload: ComplaintCreate): Promise<Complaint> {
    const { data } = await request<Complaint>('/complaints', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    return data;
  },

  async getComplaint(id: string): Promise<Complaint> {
    const { data } = await request<Complaint>(`/complaints/${id}`);
    return data;
  },

  async listComplaints(params: {
    category?: string;
    priority?: string;
    status?: string;
    page?: number;
    page_size?: number;
  } = {}): Promise<ComplaintListResponse> {
    const query = new URLSearchParams();
    if (params.category) query.append('category', params.category);
    if (params.priority) query.append('priority', params.priority);
    if (params.status) query.append('status', params.status);
    if (params.page) query.append('page', params.page.toString());
    if (params.page_size) query.append('page_size', params.page_size.toString());

    const queryString = query.toString() ? `?${query.toString()}` : '';
    const { data } = await request<ComplaintListResponse>(`/complaints${queryString}`);
    return data;
  },

  async updateComplaintStatus(id: string, newStatus: Status): Promise<Complaint> {
    const { data } = await request<Complaint>(`/complaints/${id}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status: newStatus }),
    });
    return data;
  },

  async getStats(): Promise<StatsWithCache> {
    const { data, headers } = await request<any>('/stats');
    const cacheHeader = headers.get('X-Cache')?.toUpperCase() || 'UNKNOWN';
    return {
      data,
      cacheStatus: (cacheHeader === 'HIT' || cacheHeader === 'MISS') ? cacheHeader : 'UNKNOWN',
    };
  },

  async getProvidersMeta(): Promise<ProvidersMetaResponse> {
    const { data } = await request<ProvidersMetaResponse>('/meta/providers');
    return data;
  },
};
