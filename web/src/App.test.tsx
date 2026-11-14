import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import { installFakeApi, makeShift } from "./test/fakeApi";
import { renderWithClient } from "./test/render";

afterEach(() => vi.unstubAllGlobals());

describe("App", () => {
  it("shows the login form when there is no session", async () => {
    installFakeApi([], null);
    renderWithClient(<App />);
    expect(await screen.findByRole("button", { name: "Sign in" })).toBeInTheDocument();
  });

  it("renders the team's shifts with their assignee and status", async () => {
    installFakeApi([makeShift({ title: "Prep", assignee_id: 2, assignee_name: "Ben" })]);
    renderWithClient(<App />);
    expect(await screen.findByText("Prep")).toBeInTheDocument();
    expect(screen.getByLabelText("Assignee for Prep")).toHaveValue("2");
    expect(screen.getByText("Open")).toBeInTheDocument();
  });

  it("adds a shift and shows it in the list", async () => {
    installFakeApi([]);
    renderWithClient(<App />);
    await userEvent.type(await screen.findByLabelText("New shift title"), "Dinner");
    await userEvent.type(screen.getByLabelText("Starts at"), "2030-01-02T18:00");
    await userEvent.click(screen.getByRole("button", { name: "Add shift" }));
    expect(await screen.findByText("Dinner")).toBeInTheDocument();
  });

  it("returns to the login form after signing out", async () => {
    installFakeApi([makeShift()]);
    renderWithClient(<App />);
    await userEvent.click(await screen.findByRole("button", { name: "Sign out" }));
    expect(await screen.findByRole("button", { name: "Sign in" })).toBeInTheDocument();
  });
});
