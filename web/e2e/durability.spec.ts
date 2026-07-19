import { type ChildProcess, spawn } from "node:child_process";
import { mkdtempSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { expect, type Page, test } from "@playwright/test";

const HERE = path.dirname(fileURLToPath(import.meta.url));

/**
 * Durable recovery, demonstrated rather than assumed: an edit reaches
 * FastAPI's disk, survives a real sync-server restart, and the badge
 * shows "save failed, retrying" while the backend is down and "saved"
 * once it returns.
 *
 * This spec runs as its own Playwright project and boots a complete
 * stack of its own on isolated ports, held as exact child process
 * handles. It never signals by pattern, so concurrent agents, other
 * worktrees, and the shared webServer stack are untouchable by
 * construction, and every restart waits for the old process to exit
 * before the replacement binds.
 */

// window.chessStudioEditor is declared globally in room.spec.ts.

const API_PORT = 8200;
const SYNC_PORT = 8210;
const WEB_PORT = 5273;
const APP_URL = `http://localhost:${WEB_PORT}`;

const scratch = mkdtempSync(path.join(os.tmpdir(), "euro-chess-durability-"));
const services: Set<ChildProcess> = new Set();

function spawnService(command: string, args: string[], cwd: string, env: Record<string, string>) {
  // detached puts the child in its own process group, so stopping it
  // takes down grandchildren too (uv run wraps a python process).
  const child = spawn(command, args, {
    cwd,
    env: { ...process.env, ...env },
    stdio: "ignore",
    detached: true,
  });
  services.add(child);
  return child;
}

async function stopService(child: ChildProcess): Promise<void> {
  services.delete(child);
  if (child.exitCode !== null || child.pid === undefined) return;
  const exited = new Promise<void>((resolve) => child.once("exit", () => resolve()));
  try {
    process.kill(-child.pid, "SIGTERM");
  } catch {
    return; // already gone
  }
  // The replacement must not race the dying process for the port.
  const timeout = new Promise<"timeout">((resolve) => setTimeout(() => resolve("timeout"), 5000));
  if ((await Promise.race([exited, timeout])) === "timeout") {
    try {
      process.kill(-child.pid, "SIGKILL");
    } catch {
      // already gone
    }
    await exited;
  }
}

async function waitForHttp(url: string, timeoutMs: number) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(url);
      if (response.ok) return;
    } catch {
      // not up yet
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error(`service at ${url} did not come up within ${timeoutMs}ms`);
}

function startBackend() {
  const child = spawnService(
    "uv",
    ["run", "uvicorn", "euro_chess_studio.main:app", "--port", String(API_PORT)],
    path.resolve(HERE, "../../api"),
    {
      CHESS_STUDIO_DB_PATH: path.join(scratch, "db.sqlite"),
      CHESS_STUDIO_CANVAS_DIR: path.join(scratch, "canvas"),
      CHESS_STUDIO_ASSETS_DIR: path.join(scratch, "assets"),
    },
  );
  return { child, ready: waitForHttp(`http://localhost:${API_PORT}/health`, 30_000) };
}

function startSync() {
  const child = spawnService("bun", ["sync-server/index.ts"], path.resolve(HERE, ".."), {
    CHESS_STUDIO_API_URL: `http://localhost:${API_PORT}`,
    CHESS_STUDIO_SYNC_PORT: String(SYNC_PORT),
  });
  return { child, ready: waitForHttp(`http://localhost:${SYNC_PORT}/health`, 60_000) };
}

function startWeb() {
  const child = spawnService(
    path.resolve(HERE, "../node_modules/.bin/vite"),
    ["--port", String(WEB_PORT), "--strictPort"],
    path.resolve(HERE, ".."),
    {
      CHESS_STUDIO_API_PORT: String(API_PORT),
      CHESS_STUDIO_SYNC_PORT: String(SYNC_PORT),
    },
  );
  return { child, ready: waitForHttp(APP_URL, 30_000) };
}

let backend: ChildProcess;
let sync: ChildProcess;

test.beforeAll(async () => {
  const backendStart = startBackend();
  backend = backendStart.child;
  await backendStart.ready;
  const syncStart = startSync();
  sync = syncStart.child;
  const webStart = startWeb();
  await Promise.all([syncStart.ready, webStart.ready]);
});

test.afterAll(async () => {
  await Promise.all([...services].map((child) => stopService(child)));
});

async function createNote(page: Page, id: string): Promise<void> {
  await page.evaluate((shapeId) => {
    window.chessStudioEditor?.createShape({
      id: shapeId as never,
      type: "note",
      x: 5200,
      y: 100,
    });
  }, id);
}

async function canvasContains(page: Page, id: string): Promise<boolean> {
  const response = await page.request.get(`${APP_URL}/api/canvas`);
  if (!response.ok()) return false;
  const body = (await response.json()) as { snapshot: { store: Record<string, unknown> } | null };
  return body.snapshot !== null && id in body.snapshot.store;
}

test("an edit persists to the backend, survives a sync-server restart, and the badge reports save failure and recovery", async ({
  page,
}) => {
  test.setTimeout(180_000);

  await page.goto(APP_URL);
  await page.waitForSelector("#join-name");
  await page.fill("#join-name", `Durable-${Date.now()}`);
  await page.click('button[type="submit"]');
  await expect(page.locator('[data-room-status="live"]')).toBeVisible({ timeout: 20_000 });
  // The user's own workspace shape surviving in the document proves
  // the reconnected, writable session is up (same wait as room.spec).
  await page.waitForFunction(
    () => {
      const raw = localStorage.getItem("euro-chess-studio:current-user");
      if (!raw) return false;
      const user = JSON.parse(raw) as { id: string };
      return (
        window.chessStudioEditor?.getShape(`shape:workspace-${user.id}-chess-machine` as never) !==
        undefined
      );
    },
    undefined,
    { timeout: 20_000 },
  );
  await page.waitForTimeout(800);

  // 1. The edit reaches FastAPI's disk through the room's debounced PUT.
  const note1 = `shape:durable-1-${Date.now()}`;
  await createNote(page, note1);
  await expect.poll(() => canvasContains(page, note1), { timeout: 20_000 }).toBe(true);

  // 2. A real restart: stop the owned sync process (waiting for it to
  // exit), boot a fresh one, and read the edit back through a
  // brand-new room loaded from FastAPI.
  await stopService(sync);
  const syncRestart = startSync();
  sync = syncRestart.child;
  await syncRestart.ready;
  await page.reload();
  await expect(page.locator('[data-room-status="live"]')).toBeVisible({ timeout: 30_000 });
  await page.waitForFunction(
    (id) => window.chessStudioEditor?.getShape(id as never) !== undefined,
    note1,
    { timeout: 20_000 },
  );

  // 3. Backend down: the room stays live, but durability honestly says
  // "save failed, retrying".
  await page.waitForFunction(() => window.chessStudioEditor !== undefined);
  await stopService(backend);
  const note2 = `shape:durable-2-${Date.now()}`;
  await createNote(page, note2);
  await expect(page.locator('[data-persist-status="error"]')).toBeVisible({ timeout: 30_000 });
  await expect(page.locator('[data-room-status="live"]')).toBeVisible();

  // 4. Backend back: the retry loop drains, the badge recovers, and the
  // offline-era edit is on disk.
  const backendRestart = startBackend();
  backend = backendRestart.child;
  await backendRestart.ready;
  await expect(page.locator('[data-persist-status="saved"]')).toBeVisible({ timeout: 30_000 });
  await expect.poll(() => canvasContains(page, note2), { timeout: 20_000 }).toBe(true);
});
