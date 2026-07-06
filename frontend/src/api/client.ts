import type {
  AssistantEntry,
  Order,
  PlanningProgressEvent,
  TrackingEvent,
  TripActionExecuteRequest,
  TripActionExecuteResponse,
  TripPlan,
  TripPlanResponse,
} from "../types/api";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(error || `Request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export function fetchOrders(): Promise<Order[]> {
  return request<Order[]>("/api/orders");
}

export function fetchAssistantEntry(): Promise<AssistantEntry> {
  return request<AssistantEntry>("/api/trip-assistant/entry");
}

export function createTripPlan(includeDebug = false): Promise<TripPlanResponse> {
  return request<TripPlanResponse>("/api/trip-plans", {
    method: "POST",
    body: JSON.stringify({
      userId: "u_mock_001",
      targetWindow: "nearest_weekend",
      includeDebug,
    }),
  });
}

export async function createTripPlanStream(
  onProgress: (event: PlanningProgressEvent) => void,
): Promise<TripPlanResponse> {
  const response = await fetch(`${API_BASE_URL}/api/trip-plans/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      userId: "u_mock_001",
      targetWindow: "nearest_weekend",
      includeDebug: false,
    }),
  });

  if (!response.ok || !response.body) {
    throw new Error(await response.text());
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() ?? "";

    for (const chunk of chunks) {
      const line = chunk
        .split("\n")
        .find((item) => item.startsWith("data:"));
      if (!line) {
        continue;
      }
      const event = JSON.parse(line.slice(5).trim()) as {
        type: "progress" | "heartbeat" | "final" | "error" | "done";
        payload?: Record<string, unknown>;
      };

      if (event.type === "progress") {
        onProgress(event.payload as PlanningProgressEvent);
      }
      if (event.type === "heartbeat") {
        onProgress({ progressTitle: String(event.payload?.message ?? "还在规划，马上回来") });
      }
      if (event.type === "final") {
        return event.payload as TripPlanResponse;
      }
      if (event.type === "error") {
        throw new Error(String(event.payload?.message ?? "规划失败"));
      }
    }
  }

  throw new Error("规划中断，请稍后再试");
}

export function fetchTripPlan(planId: string): Promise<TripPlan> {
  return request<TripPlan>(`/api/trip-plans/${planId}`);
}

export function trackEvent(event: TrackingEvent): Promise<{ ok: boolean; received: number }> {
  return request<{ ok: boolean; received: number }>("/api/tracking", {
    method: "POST",
    body: JSON.stringify(event),
  });
}

export function executeTripAction(action: TripActionExecuteRequest): Promise<TripActionExecuteResponse> {
  return request<TripActionExecuteResponse>("/api/trip-actions/execute", {
    method: "POST",
    body: JSON.stringify({ userId: "u_mock_001", ...action }),
  });
}
