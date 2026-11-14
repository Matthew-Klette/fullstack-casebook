/// <reference types="vitest" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const apiTarget = process.env.API_TARGET ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Same-origin in development: the browser talks to /api and Vite forwards to FastAPI.
    proxy: { "/api": { target: apiTarget, rewrite: (path) => path.replace(/^\/api/, "") } },
  },
  preview: {
    proxy: { "/api": { target: apiTarget, rewrite: (path) => path.replace(/^\/api/, "") } },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
  },
});
