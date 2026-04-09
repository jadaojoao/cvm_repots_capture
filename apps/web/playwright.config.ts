import path from "node:path";
import { defineConfig } from "@playwright/test";

const apiPort = Number(process.env.PLAYWRIGHT_API_PORT ?? "8000");
const webPort = Number(process.env.PLAYWRIGHT_WEB_PORT ?? "3000");
const apiBaseUrl = `http://127.0.0.1:${apiPort}`;

function withApiBaseUrl(command: string): string {
  if (process.platform === "win32") {
    return `powershell -Command "$env:API_BASE_URL='${apiBaseUrl}'; ${command}"`;
  }
  return `API_BASE_URL=${apiBaseUrl} ${command}`;
}

export default defineConfig({
  testDir: "./tests",
  testMatch: "**/*.spec.ts",
  workers: 1,
  timeout: 45_000,
  use: {
    baseURL: `http://127.0.0.1:${webPort}`,
    headless: true,
    trace: "on-first-retry",
  },
  webServer: [
    {
      command: `python -m uvicorn apps.api.app.main:app --host 127.0.0.1 --port ${apiPort}`,
      url: `http://127.0.0.1:${apiPort}/health`,
      cwd: path.resolve(process.cwd(), "..", ".."),
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
    {
      command: withApiBaseUrl(`npm run dev -- --port ${webPort}`),
      url: `http://127.0.0.1:${webPort}`,
      cwd: process.cwd(),
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
  ],
});
