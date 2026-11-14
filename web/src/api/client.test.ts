import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, request } from "./client";

afterEach(() => vi.unstubAllGlobals());

const json = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });

describe("request", () => {
  it("refreshes once for parallel 401s and then retries each request", async () => {
    let refreshed = false;
    const fetchMock = vi.fn(async (url: string) => {
      if (url === "/api/auth/refresh") {
        await new Promise((r) => setTimeout(r, 10));
        refreshed = true;
        return json(200, {});
      }
      return refreshed ? json(200, { ok: url }) : json(401, { detail: "expired" });
    });
    vi.stubGlobal("fetch", fetchMock);

    const results = await Promise.all([request("/a"), request("/b"), request("/c")]);

    expect(results).toEqual([{ ok: "/api/a" }, { ok: "/api/b" }, { ok: "/api/c" }]);
    const refreshCalls = fetchMock.mock.calls.filter(([u]) => u === "/api/auth/refresh");
    expect(refreshCalls).toHaveLength(1);
  });

  it("does not loop when the refresh itself is rejected", async () => {
    const fetchMock = vi.fn(async () => json(401, { detail: "nope" }));
    vi.stubGlobal("fetch", fetchMock);
    await expect(request("/a")).rejects.toMatchObject({ status: 401 });
    expect(fetchMock).toHaveBeenCalledTimes(2); // the request, then one refresh attempt
  });

  it("surfaces a 409 as a conflict ApiError with the server detail", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => json(409, { detail: { code: "version_conflict", current_version: 4 } })));
    const err = await request("/shifts/1", { method: "PATCH", body: "{}" }).catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect((err as ApiError).isConflict).toBe(true);
    expect((err as ApiError).detail).toEqual({ code: "version_conflict", current_version: 4 });
  });

  it("sends credentials and the CSRF header on every call", async () => {
    const fetchMock = vi.fn(async (_url: string, _init?: RequestInit) => json(200, {}));
    vi.stubGlobal("fetch", fetchMock);
    await request("/auth/me");
    const init = fetchMock.mock.calls[0]?.[1] as RequestInit;
    expect(init.credentials).toBe("include");
    expect(init.headers).toMatchObject({ "X-Requested-With": "shiftboard" });
  });
});
