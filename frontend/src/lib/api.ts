const API_URL = typeof window === "undefined"
  ? (process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000")
  : "/api-backend";

export interface ActivitySummary {
  id: string;
  name: string;
  wbs_ref: string | null;
  discipline: string | null;
  reported_progress: number;
  evidence_score: number;
  confidence_score: number;
  missing_evidence: string | null;
  verification_required: boolean;
  updated_at: string | null;
}

export interface EvidenceItem {
  id: string;
  source_system: string;
  ingesting_connector: string;
  provenance_ref: string | null;
  extracted_content: string;
  source_excerpt: string | null;
  relation_type: string;
  source_reliability_signal: string;
  timestamp: string;
  ingested_at: string;
}

export interface ActivityDetail extends ActivitySummary {
  confidence_reasoning: string | null;
  evidence_items: EvidenceItem[];
}

export interface Report {
  id: string;
  draft_content: string;
  edited_content: string | null;
  created_at: string;
  confirmed_at: string | null;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatResponse {
  answer: string;
  evidence_refs: string[];
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json();
}

export const api = {
  activities: {
    list: () => request<ActivitySummary[]>("/activities"),
    get: (id: string) => request<ActivityDetail>(`/activities/${id}`),
    confirm: (id: string, fieldName: string, currentValue: string) =>
      request(`/activities/${id}/confirm`, {
        method: "POST",
        body: JSON.stringify({ field_name: fieldName, current_value: currentValue }),
      }),
    correct: (id: string, fieldName: string, oldValue: string, newValue: string, rationale?: string) =>
      request<ActivityDetail>(`/activities/${id}/correct`, {
        method: "POST",
        body: JSON.stringify({ field_name: fieldName, old_value: oldValue, new_value: newValue, rationale }),
      }),
    recompute: (id: string) =>
      request(`/activities/${id}/recompute`, { method: "POST" }),
  },

  ingestion: {
    recomputeAll: () =>
      request("/ingest/recompute-all", { method: "POST" }),
    uploadSchedule: (file: File) => {
      const form = new FormData();
      form.append("file", file);
      return fetch(`/api-backend/ingest/schedule`, { method: "POST", body: form }).then(r => r.json());
    },
    uploadDocument: (file: File) => {
      const form = new FormData();
      form.append("file", file);
      return fetch(`/api-backend/ingest/document`, { method: "POST", body: form }).then(r => r.json());
    },
    uploadBoq: (file: File) => {
      const form = new FormData();
      form.append("file", file);
      return fetch(`/api-backend/ingest/boq`, { method: "POST", body: form }).then(r => r.json());
    },
  },

  reports: {
    list: () => request<Report[]>("/reports"),
    draft: () => request<Report>("/reports/draft", { method: "POST" }),
    get: (id: string) => request<Report>(`/reports/${id}`),
    edit: (id: string, content: string) =>
      request<Report>(`/reports/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ edited_content: content }),
      }),
    send: (id: string) =>
      request(`/reports/${id}/send`, { method: "POST" }),
  },

  chat: {
    send: (activityId: string, message: string, history: ChatMessage[]) =>
      request<ChatResponse>("/chat", {
        method: "POST",
        body: JSON.stringify({ activity_id: activityId, message, history }),
      }),
  },
};
