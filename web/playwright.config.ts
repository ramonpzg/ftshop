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
      env: {
        CHESS_STUDIO_DB_PATH: e2eDbPath,
        CHESS_STUDIO_CANVAS_DIR: e2eCanvasDir,
        CHESS_STUDIO_ASSETS_DIR: e2eAssetsDir,
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
      executablePath: "/opt/pw-browsers/chromium",
    },
  },
});
