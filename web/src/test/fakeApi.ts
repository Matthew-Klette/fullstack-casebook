import { vi } from "vitest";
import type { Member, Shift, User } from "../api/client";

export interface FakeServer {
  shifts: Shift[];
  calls: { method: string; path: string; body?: unknown }[];
  /** When set, the next PATCH answers 409 and bumps the stored version. */
  conflictOnNextPatch: boolean;
}

export const manager: User = {
  id: 1,
  email: "ana@example.test",
  name: "Ana",
  teams: [{ id: 10, name: "Kitchen", role: "manager" }],
};

export const members: Member[] = [
  { id: 1, name: "Ana", role: "manager" },
  { id: 2, name: "Ben", role: "member" },
];

export function makeShift(over: Partial<Shift> = {}): Shift {
  return {
    id: 100,
    team_id: 10,
    title: "Prep",
    notes: "",
    starts_at: "2030-01-01T08:00:00Z",
    status: "open",
    assignee_id: null,
    assignee_name: null,
    version: 1,
    ...over,
  };
}

const reply = (status: number, body?: unknown) =>
  new Response(body === undefined ? null : JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });

/** An in-memory stand-in for the API, installed as global fetch. */
export function installFakeApi(initial: Shift[] = [makeShift()], initialUser: User | null = manager): FakeServer {
  let user = initialUser;
  const server: FakeServer = { shifts: initial.map((s) => ({ ...s })), calls: [], conflictOnNextPatch: false };

  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init: RequestInit = {}) => {
      const path = url.replace(/^\/api/, "");
      const method = init.method ?? "GET";
      const body = init.body ? JSON.parse(String(init.body)) : undefined;
      server.calls.push({ method, path, body });

      if (path === "/auth/logout") {
        user = null;
        return reply(204);
      }
      if (path === "/auth/me") return user ? reply(200, user) : reply(401, { detail: "not authenticated" });
      if (path === "/teams/10/members") return reply(200, members);
      if (path === "/teams/10/shifts" && method === "GET") return reply(200, server.shifts);
      if (path === "/teams/10/shifts" && method === "POST") {
        const created = makeShift({ id: 200 + server.shifts.length, title: body.title, starts_at: body.starts_at });
        server.shifts.push(created);
        return reply(201, created);
      }
      const patch = path.match(/^\/shifts\/(\d+)$/);
      if (patch && method === "PATCH") {
        const shift = server.shifts.find((s) => s.id === Number(patch[1]));
        if (!shift) return reply(404, { detail: "shift not found" });
        if (server.conflictOnNextPatch || body.version !== shift.version) {
          server.conflictOnNextPatch = false;
          shift.version += 1;
          return reply(409, { detail: { code: "version_conflict", current_version: shift.version } });
        }
        Object.assign(shift, { status: body.status ?? shift.status, title: body.title ?? shift.title });
        shift.version += 1;
        return reply(200, shift);
      }
      return reply(404, { detail: `unhandled ${method} ${path}` });
    }),
  );
  return server;
}
