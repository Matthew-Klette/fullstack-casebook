import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import { installFakeApi, makeShift } from "./test/fakeApi";
import { renderWithClient } from "./test/render";

afterEach(() => vi.unstubAllGlobals());

describe("shift list cache after a mutation", () => {
  it("shows the new status without a reload after Mark done", async () => {
    installFakeApi([makeShift({ title: "Prep" })]);
    renderWithClient(<App />);
    const row = (await screen.findByText("Prep")).closest("li")!;

    await userEvent.click(within(row).getByRole("button", { name: "Mark done" }));

    expect(await within(row).findByText("Done")).toBeInTheDocument();
    expect(within(row).getByRole("button", { name: "Reopen" })).toBeInTheDocument();
  });

  it("refetches the team list right after the PATCH", async () => {
    const server = installFakeApi([makeShift({ title: "Prep" })]);
    renderWithClient(<App />);
    await userEvent.click(await screen.findByRole("button", { name: "Mark done" }));
    await screen.findByText("Done");

    const trail = server.calls.map((c) => `${c.method} ${c.path}`).filter((c) => c.includes("shift"));
    expect(trail).toEqual(["GET /teams/10/shifts", "PATCH /shifts/100", "GET /teams/10/shifts"]);
  });

  it("refetches after a 409 so the user sees the other person's version", async () => {
    const server = installFakeApi([makeShift({ title: "Prep" })]);
    server.conflictOnNextPatch = true;
    renderWithClient(<App />);
    await userEvent.click(await screen.findByRole("button", { name: "Mark done" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Someone else changed this shift first");
    const gets = server.calls.filter((c) => c.method === "GET" && c.path === "/teams/10/shifts");
    expect(gets).toHaveLength(2);
  });
});
