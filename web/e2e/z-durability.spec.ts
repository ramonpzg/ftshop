import { type ChildProcess, execSync, spawn } from "node:child_process";
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
 * The file sorts last (z-) on purpose: it kills and respawns the
 * webServer-managed processes, and nothing should run after it. The
 * respawned processes reuse the scratch state paths published through
 * the Playwright config metadata.
 */

// window.chessStudioEditor is declared globally in room.spec.ts.

const SYNC_PATTERN = "sync-server/index.ts";
const BACKEND_PATTERN = "uvicorn euro_chess_studio.main:app";

const spawned: ChildProcess[] = [];

function kill(pattern: string) {
  try {
    execSync(`pkill -f "${pattern}"`);
  } catch {
    // pkill exits 1 when nothing matched; that just means it was
    // already down.
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

function metadata() {
  return test.info().config.metadata as {
    e2eDbPath: string;
    e2eCanvasDir: string;
    e2eAssetsDir: string;
  };
}

function respawnSync() {
  const child = spawn("bun", ["sync-server/index.ts"], {
    cwd: path.resolve(HERE, ".."),
    env: {
      ...process.env,
      CHESS_STUDIO_API_URL: "http://localhost:8000",
      CHESS_STUDIO_SYNC_PORT: "8010",
    },
    stdio: "ignore",
  });
  spawned.push(child);
  return waitForHttp("http://localhost:8010/health", 30_000);
}

function respawnBackend() {
  const meta = metadata();
  const child = spawn("uv", ["run", "uvicorn", "euro_chess_studio.main:app", "--port", "8000"], {
    cwd: path.resolve(HERE, "../../api"),
    env: {
      ...process.env,
      CHESS_STUDIO_DB_PATH: meta.e2eDbPath,
      CHESS_STUDIO_CANVAS_DIR: meta.e2eCanvasDir,
      CHESS_STUDIO_ASSETS_DIR: meta.e2eAssetsDir,
    },
    stdio: "ignore",
  });
  spawned.push(child);
  return waitForHttp("http://localhost:8000/health", 30_000);
}

test.afterAll(() => {
  for (const child of spawned) child.kill("SIGTERM");
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
  const response = await page.request.get("/api/canvas");
  if (!response.ok()) return false;
  const body = (await response.json()) as { snapshot: { store: Record<string, unknown> } | null };
  return body.snapshot !== null && id in body.snapshot.store;
}

test("an edit persists to the backend, survives a sync-server restart, and the badge reports save failure and recovery", async ({
  page,
}) => {
  test.setTimeout(180_000);

  await page.goto("/");
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

  // 2. A real restart: kill the sync process, boot a fresh one, and read
  // the edit back through a brand-new room loaded from FastAPI.
  kill(SYNC_PATTERN);
  await respawnSync();
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
  kill(BACKEND_PATTERN);
  const note2 = `shape:durable-2-${Date.now()}`;
  await createNote(page, note2);
  await expect(page.locator('[data-persist-status="error"]')).toBeVisible({ timeout: 30_000 });
  await expect(page.locator('[data-room-status="live"]')).toBeVisible();

  // 4. Backend back: the retry loop drains, the badge recovers, and the
  // offline-era edit is on disk.
  await respawnBackend();
  await expect(page.locator('[data-persist-status="saved"]')).toBeVisible({ timeout: 30_000 });
  await expect.poll(() => canvasContains(page, note2), { timeout: 20_000 }).toBe(true);
});
