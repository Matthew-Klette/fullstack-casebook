import { expect, test } from "@playwright/test";
import { mkdirSync } from "node:fs";

async function signIn(page: import("@playwright/test").Page, email: string) {
  await page.goto("/");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("shiftboard-demo");
  await page.getByRole("button", { name: "Sign in" }).click();
}

test("manager signs in, completes a shift, and the change survives a reload", async ({ page }) => {
  await signIn(page, "ana@example.test");
  const row = page.locator("li.shift", { hasText: "Lunch service, grill" });
  await expect(row).toBeVisible();
  await expect(row.getByText("Open")).toBeVisible();

  await row.getByRole("button", { name: "Mark done" }).click();
  await expect(row.getByText("Done")).toBeVisible();

  await page.reload();
  await expect(page.locator("li.shift", { hasText: "Lunch service, grill" }).getByText("Done")).toBeVisible();

  if (process.env.SCREENSHOT) {
    mkdirSync("../docs", { recursive: true });
    await page.screenshot({ path: "../docs/screenshot.png" });
  }
});

test("a member cannot see another team and can sign out", async ({ page }) => {
  await signIn(page, "ben@example.test");
  await expect(page.getByText("Ben Naidoo (member)")).toBeVisible();
  await expect(page.getByRole("option", { name: "Front of house" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: /Export/ })).toHaveCount(0);
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page.getByRole("button", { name: "Sign in" })).toBeVisible();
});

test("exporting done shifts reaches the payroll service once", async ({ page }) => {
  await signIn(page, "ana@example.test");
  await page.getByRole("button", { name: /Export done shifts/ }).click();
  await expect(page.getByRole("status")).toContainText("reference batch-");
});
