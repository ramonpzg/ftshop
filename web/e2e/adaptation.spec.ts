import { expect, test } from "@playwright/test";

/** The presenter's evidence chain, driven end to end in a real browser
 * against the real stack with no provider keys: seeded state renders,
 * training replays with cached provenance, both benchmarks run, and
 * the comparison shows a signed improvement next to a signed
 * regression. */
test("the adaptation chain runs from the board without a shell", async ({ page }) => {
  await page.goto("/?presenter=1");
  await page.waitForSelector("#join-name");
  await page.fill("#join-name", `Presenter-${Date.now()}`);
  await page.click('button[type="submit"]');
  await expect(page.locator('[data-testid^="workspace-panel-"]').first()).toBeAttached();

  // The panel sits left of the workspace grid; bring it into view so
  // tldraw does not cull its HTML container.
  await page.waitForFunction(() => {
    const editor = (window as unknown as { chessStudioEditor?: unknown }).chessStudioEditor;
    return editor !== undefined;
  });
  await page.evaluate(() => {
    // biome-ignore lint/suspicious/noExplicitAny: e2e debug hook
    const editor = (window as any).chessStudioEditor;
    const bounds = editor.getShapePageBounds("shape:adaptation-panel");
    editor.zoomToBounds(bounds, { inset: 32 });
  });

  const panel = page.getByTestId("adaptation-panel");
  await expect(panel).toBeVisible();
  await panel.dblclick({ force: true });

  // Seeded identities render before anything runs.
  await expect(page.getByTestId("snapshot-card")).toBeVisible();
  await expect(page.getByTestId("snapshot-hash")).not.toHaveText("-");
  await expect(page.getByTestId("suite-card")).toBeVisible();
  const suitePsid = await page.getByTestId("suite-psid").textContent();
  expect(suitePsid).not.toBe("-");
  // Keyless run: no live benchmark button exists.
  await expect(page.getByTestId("bench-base-live")).toHaveCount(0);

  // Train: a cached replay with visible provenance.
  await page.getByTestId("train-adapter").click();
  await expect(page.getByTestId("adapter-card")).toBeVisible({ timeout: 10_000 });
  await expect(page.getByTestId("adapter-source")).toHaveText("cached");
  await expect(page.getByTestId("adapter-dataset-hash")).not.toHaveText("-");

  // Benchmark both checkpoints on the frozen suite.
  await page.getByTestId("bench-base").click();
  await expect(page.getByTestId("benchmark-runs")).toBeVisible({ timeout: 10_000 });
  await page.getByTestId("bench-adapted").click();
  await expect(page.getByTestId("comparison")).toBeVisible({ timeout: 10_000 });

  // Both runs measured the suite's exact position set.
  await expect(page.getByText("position set matches suite").first()).toBeVisible();

  // The comparison teaches the trade-off: one delta up, one down, in
  // words.
  await expect(page.getByTestId("delta-model_legal_move_rate")).toContainText("improved");
  await expect(page.getByTestId("delta-explanation_rate")).toContainText("regressed");
});

/** The modality evidence reveal: the audio chain renders a playable
 * local pair, and the files themselves are served by the backend. */
test("audio adaptation evidence reveals playable local media", async ({ page }) => {
  await page.goto("/");
  await page.waitForSelector("#join-name");
  await page.fill("#join-name", `Media-${Date.now()}`);
  await page.click('button[type="submit"]');
  await expect(page.locator('[data-testid^="workspace-panel-"]').first()).toBeAttached();

  await page.getByTestId("page-tab-board-sound").click();
  // The modality panel sits below the seeded notes; bring it into view
  // so tldraw does not cull its HTML container.
  await page.evaluate(() => {
    // biome-ignore lint/suspicious/noExplicitAny: e2e debug hook
    const editor = (window as any).chessStudioEditor;
    const bounds = editor.getShapePageBounds("shape:modality-panel-board-sound");
    editor.zoomToBounds(bounds, { inset: 32 });
  });
  const panel = page.getByTestId("modality-panel-audio");
  await expect(panel).toBeVisible();
  await panel.dblclick({ force: true });

  await page.getByTestId("run-job-audio.adaptation_evidence").click();
  await expect(page.getByTestId("artifact-before-after")).toBeVisible({ timeout: 10_000 });
  await expect(page.getByTestId("artifact-before")).toBeVisible();
  await expect(page.getByTestId("artifact-after")).toBeVisible();
  await expect(page.getByTestId("evidence-metrics")).toBeVisible();
  // The regression is written into the cached metric rows.
  await expect(page.getByTestId("evidence-metrics")).toContainText("regressed");

  // The referenced media is served with real bytes, no provider URL.
  const clip = await page.request.get("/api/artifacts/media/audio/board_music_adapted.wav");
  expect(clip.status()).toBe(200);
  expect((await clip.body()).byteLength).toBeGreaterThan(10_000);
  const waveform = await page.request.get(
    "/api/artifacts/media/audio/board_music_adapted_waveform.png",
  );
  expect(waveform.status()).toBe(200);
});
