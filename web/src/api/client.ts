import type { components } from "./schema";

export type User = components["schemas"]["UserOut"];
export type Team = components["schemas"]["TeamOut"];
export type Member = components["schemas"]["MemberOut"];
export type Shift = components["schemas"]["ShiftOut"];
export type ShiftCreate = components["schemas"]["ShiftCreate"];
export type ShiftUpdate = components["schemas"]["ShiftUpdate"];
export type PayrollExport = components["schemas"]["ExportOut"];

const BASE: string = import.meta.env.VITE_API_BASE ?? "/api";

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly detail: unknown,
  ) {
    super(typeof detail === "string" ? detail : `request failed with ${status}`);
  }
  get isConflict(): boolean {
    return this.status === 409;
  }
}

function send(path: string, init: RequestInit = {}): Promise<Response> {
  return fetch(BASE + path, {
    ...init,
    credentials: "include",
    headers: {
      "X-Requested-With": "shiftboard",
      ...(init.body ? { "Content-Type": "application/json" } : {}),
      ...init.headers,
    },
  });
}

// One refresh at a time. Parallel 401s must share a single rotation, because the API treats a
// second use of a rotated refresh token as theft and ends the session.
let inflightRefresh: Promise<boolean> | null = null;

export function refreshSession(): Promise<boolean> {
  inflightRefresh ??= send("/auth/refresh", { method: "POST" })
    .then((res) => res.ok)
    .catch(() => false)
    .finally(() => {
      inflightRefresh = null;
    });
  return inflightRefresh;
}

export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let res = await send(path, init);
  if (res.status === 401 && !path.startsWith("/auth/") && (await refreshSession())) {
    res = await send(path, init);
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, (body as { detail?: unknown }).detail ?? null);
  }
  return res.status === 204 ? (undefined as T) : ((await res.json()) as T);
}

const json = (method: string, body: unknown): RequestInit => ({ method, body: JSON.stringify(body) });

export const api = {
  login: (email: string, password: string) => request<User>("/auth/login", json("POST", { email, password })),
  logout: () => request<void>("/auth/logout", { method: "POST" }),
  me: () => request<User>("/auth/me"),
  members: (teamId: number) => request<Member[]>(`/teams/${teamId}/members`),
  shifts: (teamId: number) => request<Shift[]>(`/teams/${teamId}/shifts`),
  createShift: (teamId: number, body: ShiftCreate) =>
    request<Shift>(`/teams/${teamId}/shifts`, json("POST", body)),
  updateShift: (id: number, body: ShiftUpdate) => request<Shift>(`/shifts/${id}`, json("PATCH", body)),
  deleteShift: (id: number) => request<void>(`/shifts/${id}`, { method: "DELETE" }),
  exportPayroll: (teamId: number) => request<PayrollExport>(`/teams/${teamId}/exports`, { method: "POST" }),
};
