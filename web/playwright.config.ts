import os from "node:os";
import path from "node:path";
import { defineConfig } from "@playwright/test";

const e2eStamp = Date.now();
const e2eDbPath = path.join(os.tmpdir(), `euro-chess-studio-e2e-${e2eStamp}.db`);
// The canvas snapshot and asset dirs must also point at scratch space,
// or e2e runs would overwrite the presenter's real authored deck.
const e2eCanvasDir = path.join(os.tmpdir(), `euro-chess-studio-e2e-${e2eStamp}-canvas`);
const e2eAssetsDir = path.join(os.tmpdir(), `euro-chess-studio-e2e-${e2eStamp}-assets`);

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  fullyParallel: false,
  workers: 1,
  webServer: [
    {
      command: "uv run uvicorn euro_chess_studio.main:app --port 8000",
      cwd: "../api",
      url: "http://localhost:8000/health",
      reuseExistingServer: false,
      timeout: 30_000,
      env: {
        CHESS_STUDIO_DB_PATH: e2eDbPath,
        CHESS_STUDIO_CANVAS_DIR: e2eCanvasDir,
        CHESS_STUDIO_ASSETS_DIR: e2eAssetsDir,
      },
    },
    {
      // The sync room. It waits for the backend itself (retrying
      // GET /canvas), so parallel startup is safe.
      command: "bun sync-server/index.ts",
      url: "http://localhost:8010/health",
      reuseExistingServer: false,
      timeout: 60_000,
      env: {
        CHESS_STUDIO_API_URL: "http://localhost:8000",
        CHESS_STUDIO_SYNC_PORT: "8010",
      },
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
      // Playwright's own browser discovery by default. The previous
      // hardcoded /opt/pw-browsers/chromium only existed on one
      // machine; that machine can still opt in through this env var.
      // The full release command surface is phase 36's job.
      executablePath: process.env.CHESS_STUDIO_CHROMIUM ?? undefined,
    },
  },
});
