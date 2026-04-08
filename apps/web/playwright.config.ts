import path from "node:path";
import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  timeout: 45_000,
  use: {
    baseURL: "http://127.0.0.1:3000",
    headless: true,
    trace: "on-first-retry",
  },
  webServer: [
    {
      command: "python -m uvicorn apps.api.app.main:app --host 127.0.0.1 --port 8000",
      url: "http://127.0.0.1:8000/health",
      cwd: path.resolve(process.cwd(), "..", ".."),
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
    {
      command: "npm run dev",
      url: "http://127.0.0.1:3000",
      cwd: process.cwd(),
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
  ],
});
