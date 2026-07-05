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

test("playing a legal move records a dataset row visible in the workspace", async ({ page }) => {
  const name = `Smoke-${Date.now()}`;
  await page.goto("/");
  await page.waitForSelector("#join-name");
  await page.fill("#join-name", name);
  await page.click('button[type="submit"]');

  const workspacePanel = page.locator('[data-testid^="workspace-panel-"]').first();
  await expect(workspacePanel).toBeAttached();
  await workspacePanel.dblclick({ force: true });

  await expect(page.locator('[data-testid="square-e2"]')).toBeVisible();
  await page.locator('[data-testid="square-e2"]').click();
  await page.locator('[data-testid="square-e4"]').click();

  await expect(page.locator("text=FEN -> move")).toBeVisible();
});
