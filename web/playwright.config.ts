import { defineConfig } from "@playwright/test";

// One worker, one headless Chromium. The API gets a throwaway SQLite file seeded with demo data.
const api = "../api/.venv/bin/python";

export default defineConfig({
  testDir: "./e2e",
  workers: 1,
  fullyParallel: false,
  retries: 0,
  reporter: "list",
  use: { baseURL: "http://127.0.0.1:5174", headless: true, viewport: { width: 1100, height: 900 } },
  webServer: [
    {
      command: `rm -f e2e.db && ${api} -m app.seed && ${api} -m uvicorn app.main:app_factory --factory --port 8100`,
      cwd: "../api",
      url: "http://127.0.0.1:8100/health",
      env: { SHIFTBOARD_DATABASE_URL: "sqlite:///./e2e.db", SHIFTBOARD_PAYROLL_URL: "http://127.0.0.1:9101" },
      reuseExistingServer: false,
      timeout: 60_000,
    },
    {
      command: `${api} -m app.integrations.payroll_stub --port 9101`,
      cwd: "../api",
      port: 9101,
      reuseExistingServer: false,
    },
    {
      command: "npx vite --host 127.0.0.1 --port 5174 --strictPort",
      env: { API_TARGET: "http://127.0.0.1:8100" },
      url: "http://127.0.0.1:5174",
      reuseExistingServer: false,
    },
  ],
});
