import os from "node:os";
import path from "node:path";
import { defineConfig } from "@playwright/test";

const e2eDbPath = path.join(os.tmpdir(), `euro-chess-studio-e2e-${Date.now()}.db`);

export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  fullyParallel: false,
  workers: 1,
  webServer: [
    {
      command: "uv run uvicorn euro_chess_studio.main:app --port 8000",
      cwd: "../api",
      url: "http://localhost:8000/health",
      reuseExistingServer: false,
      timeout: 30_000,
      env: { CHESS_STUDIO_DB_PATH: e2eDbPath },
    },
    {
      command: "bun run dev",
      url: "http://localhost:5173",
      reuseExistingServer: false,
      timeout: 30_000,
    },
  ],
  use: {
    baseURL: "http://localhost:5173",
    launchOptions: {
      executablePath: "/opt/pw-browsers/chromium",
    },
  },
});
