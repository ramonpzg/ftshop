import { expect, test } from "@playwright/test";

const PAGE_SLUGS = [
  "presentation",
  "chess-machine",
  "painting-pieces",
  "board-sound",
  "real-world-video",
];

test("all five workshop pages are reachable", async ({ page }) => {
  await page.goto("/");
  await page.waitForSelector("#join-name");
  for (const slug of PAGE_SLUGS) {
    await expect(page.locator(`[data-testid="page-tab-${slug}"]`)).toBeVisible();
  }
});

test("a new attendee can join and see their workspace and themselves in the attendee list", async ({
  page,
}) => {
  const name = `Smoke-${Date.now()}`;
  await page.goto("/");
  await page.waitForSelector("#join-name");
  await page.fill("#join-name", name);
  await page.click('button[type="submit"]');

  await expect(page.locator('[data-testid^="workspace-panel-"]').first()).toBeAttached();
  await expect(page.locator(`text=${name}`).first()).toBeVisible();
});

test("the canvas saves to the backend and survives a reload in a fresh session", async ({
  browser,
}) => {
  const contextA = await browser.newContext();
  const pageA = await contextA.newPage();
  await pageA.goto("/");
  await pageA.waitForSelector("#join-name");
  // Seeding the five pages is itself a document change, so the badge
  // must reach saved without any user action.
  await expect(pageA.locator('[data-save-status="saved"]')).toBeVisible({ timeout: 15_000 });
  await contextA.close();

  // A brand-new context has no local storage or IndexedDB. Everything
  // it sees comes from the backend snapshot.
  const contextB = await browser.newContext();
  const pageB = await contextB.newPage();
  await pageB.goto("/");
  await pageB.waitForSelector("#join-name");
  // The restored document arrives from the backend, then tldraw mounts.
  await expect(pageB.locator('[data-testid="page-tab-presentation"]')).toBeVisible({
    timeout: 15_000,
  });
  for (const slug of PAGE_SLUGS) {
    await expect(pageB.locator(`[data-testid="page-tab-${slug}"]`)).toBeVisible();
  }
  await expect(pageB.getByTestId("slide-controls")).toBeVisible();
  await contextB.close();
});

test("playing a legal move records a dataset row visible in the workspace", async ({ page }) => {
  const name = `Smoke-${Date.now()}`;
  await page.goto("/");
  await page.waitForSelector("#join-name");
  await page.fill("#join-name", name);
  await page.click('button[type="submit"]');

  // The canvas persists across sessions, so workspaces from earlier
  // tests are legitimately still on the page. Scope everything to the
  // panel this attendee owns.
  const workspacePanel = page.locator(".workspace-panel-own");
  await expect(workspacePanel).toBeAttached();
  await workspacePanel.dblclick({ force: true });

  await expect(workspacePanel.locator('[data-testid="square-e2"]')).toBeVisible();
  await workspacePanel.locator('[data-testid="square-e2"]').click();
  await workspacePanel.locator('[data-testid="square-e4"]').click();

  await expect(workspacePanel.locator("text=FEN -> move")).toBeVisible();
});
