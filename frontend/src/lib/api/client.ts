import type { paths } from "./schema";

export class ApiError extends Error {
  code: string;
  details: Record<string, unknown>;
  requestId: string;
  statusCode: number;

  constructor(code: string, message: string, statusCode: number, details = {}, requestId = "") {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.statusCode = statusCode;
    this.details = details;
    this.requestId = requestId;
  }
}

// Current demo user stored in localStorage (default to Aarav: ID 1)
const DEMO_USER_STORAGE_KEY = "dialecto_demo_user_id";

export function getActiveDemoUserId(): number {
  if (typeof window === "undefined") return 1;
  const saved = localStorage.getItem(DEMO_USER_STORAGE_KEY);
  return saved ? parseInt(saved, 10) : 1;
}

export function setActiveDemoUserId(userId: number): void {
  if (typeof window !== "undefined") {
    localStorage.setItem(DEMO_USER_STORAGE_KEY, userId.toString());
  }
}

export async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const userId = getActiveDemoUserId();
  const headers = new Headers(options.headers || {});
  headers.set("Content-Type", "application/json");
  headers.set("X-Demo-User-Id", userId.toString());

  const response = await fetch(endpoint, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorData: { error?: { code?: string; message?: string; details?: Record<string, unknown>; request_id?: string } } = {};
    try {
      errorData = await response.json();
    } catch {
      // Non-json error response
    }
    const err = errorData.error;
    throw new ApiError(
      err?.code || "unknown_error",
      err?.message || `Request failed with status ${response.status}`,
      response.status,
      err?.details || {},
      err?.request_id || response.headers.get("X-Request-Id") || ""
    );
  }

  return response.json() as Promise<T>;
}

export type User = paths["/api/v1/users"]["get"]["responses"][200]["content"]["application/json"][number];

export const api = {
  getUsers: (includeSimulated = false) =>
    apiFetch<User[]>(`/api/v1/users?include_simulated=${includeSimulated}`),
  getMe: () => apiFetch<User>("/api/v1/me"),
  getHealth: () => apiFetch<{ status: string }>("/health"),
  getReady: () => apiFetch<{ status: string; database: string }>("/ready"),
};
