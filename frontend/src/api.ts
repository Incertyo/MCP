import type {
  AccountInput,
  AccountProfile,
  ChatMessage,
  ChatResponse,
  DashboardResponse,
  EventItem,
  ObservabilitySummary,
  Recommendation,
} from "./types";

const API_BASE =
  import.meta.env.VITE_API_BASE?.replace(/\/$/, "") ??
  (typeof window !== "undefined" ? `${window.location.origin}/api` : "http://localhost:8000/api");

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!response.ok) {
    let message = `Request failed with ${response.status}`;
    try {
      const payload = await response.json();
      if (payload?.detail && typeof payload.detail === "string") {
        message = payload.detail;
      }
    } catch {
      // ignore parse errors
    }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

export const api = {
  getDashboard: () => request<DashboardResponse>("/dashboard"),
  getAccount: () => request<AccountProfile | null>("/account"),
  createAccount: (payload: AccountInput) => request<AccountProfile>("/account", { method: "POST", body: JSON.stringify(payload) }),
  getRecommendations: () => request<Recommendation[]>("/recommendations"),
  acceptRecommendation: (id: string) => request<Recommendation>(`/recommendations/${id}/accept`, { method: "POST" }),
  rejectRecommendation: (id: string) => request<Recommendation>(`/recommendations/${id}/reject`, { method: "POST" }),
  recurRecommendation: (id: string) => request<Recommendation>(`/recommendations/${id}/recur`, { method: "POST" }),
  getChatHistory: () => request<ChatMessage[]>("/chat"),
  sendChatMessage: (message: string) => request<ChatResponse>("/chat", { method: "POST", body: JSON.stringify({ message }) }),
  clearChatHistory: () => request<{ status: string }>("/chat/clear", { method: "POST" }),
  getEvents: () => request<EventItem[]>("/events"),
  clearEvents: () => request<{ status: string }>("/events/clear", { method: "POST" }),
  getObservability: () => request<ObservabilitySummary>("/observability"),
  clearObservability: () => request<{ status: string }>("/observability/clear", { method: "POST" }),
};
