import { type Browser, expect, type Page, test } from "@playwright/test";

/**
 * Multi-client acceptance for the shared room. Each test drives two or
 * three real browser contexts against the same sync room. The live
 * tldraw editor is reached through the deliberate window hook
 * (chessStudioEditor) so assertions read actual document state instead
 * of guessing at pixels.
 */

declare global {
  interface Window {
    chessStudioEditor?: {
      createShape(shape: Record<string, unknown>): void;
      updateShape(shape: Record<string, unknown>): void;
      deleteShape(id: string): void;
      getShape(id: string): { x: number; y: number; meta: Record<string, unknown> } | undefined;
      getCurrentPageId(): string;
      setCurrentPage(id: string): void;
      getViewportPageBounds(): { x: number; y: number; w: number; h: number };
      getPages(): Array<{ id: string }>;
      deletePage(id: string): void;
    };
  }
}

async function joinAs(page: Page, name: string): Promise<void> {
  await page.goto("/");
  await page.waitForSelector("#join-name");
  await page.fill("#join-name", name);
  await page.click('button[type="submit"]');
  // Joining reconnects the room with the new identity. The user's own
  // workspace shape appearing in the document (not the DOM: presenter
  // mode may legitimately be looking at another page) proves the
  // reconnected session is writable.
  await expect(page.locator('[data-room-status="live"]')).toBeVisible({ timeout: 20_000 });
  await page.waitForFunction(
    () => {
      const raw = localStorage.getItem("euro-chess-studio:current-user");
      if (!raw) return false;
      const user = JSON.parse(raw) as { id: string };
      const shapeId = `shape:workspace-${user.id}-chess-machine`;
      return window.chessStudioEditor?.getShape(shapeId as never) !== undefined;
    },
    undefined,
    { timeout: 20_000 },
  );
  // The pre-join read-only editor can hold the shape optimistically for
  // a moment before the server rebases it away; require it to survive.
  await page.waitForTimeout(800);
  await page.waitForFunction(() => {
    const raw = localStorage.getItem("euro-chess-studio:current-user");
    if (!raw) return false;
    const user = JSON.parse(raw) as { id: string };
    const shapeId = `shape:workspace-${user.id}-chess-machine`;
    return window.chessStudioEditor?.getShape(shapeId as never) !== undefined;
  });
}

async function openAttendee(browser: Browser, name: string) {
  const context = await browser.newContext();
  const page = await context.newPage();
  await joinAs(page, name);
  return { context, page };
}

async function createNote(page: Page, id: string, x: number, y: number): Promise<void> {
  await page.evaluate(
    ([shapeId, sx, sy]) => {
      window.chessStudioEditor?.createShape({
        id: shapeId as never,
        type: "note",
        x: sx as number,
        y: sy as number,
      });
    },
    [id, x, y] as const,
  );
}

function hasShape(page: Page, id: string) {
  return page.evaluate(
    (shapeId) => window.chessStudioEditor?.getShape(shapeId as never) !== undefined,
    id,
  );
}

test("two browsers edit concurrently, reload, and both edits remain", async ({ browser }) => {
  const a = await openAttendee(browser, `Ada-${Date.now()}`);
  const b = await openAttendee(browser, `Grace-${Date.now()}`);

  const noteA = `shape:e2e-a-${Date.now()}`;
  const noteB = `shape:e2e-b-${Date.now()}`;
  await Promise.all([createNote(a.page, noteA, 4000, 100), createNote(b.page, noteB, 4300, 100)]);

  // Each browser receives the other's shape over sync.
  await a.page.waitForFunction(
    (id) => window.chessStudioEditor?.getShape(id as never) !== undefined,
    noteB,
    { timeout: 15_000 },
  );
  await b.page.waitForFunction(
    (id) => window.chessStudioEditor?.getShape(id as never) !== undefined,
    noteA,
    { timeout: 15_000 },
  );

  // Both reload; the room state comes back from the server, and no
  // stale local snapshot replaces anyone's work.
  await a.page.reload();
  await expect(a.page.locator('[data-room-status="live"]')).toBeVisible({ timeout: 20_000 });
  await a.page.waitForFunction(() => window.chessStudioEditor !== undefined);
  await b.page.reload();
  await expect(b.page.locator('[data-room-status="live"]')).toBeVisible({ timeout: 20_000 });
  await b.page.waitForFunction(() => window.chessStudioEditor !== undefined);

  for (const page of [a.page, b.page]) {
    await page.waitForFunction(
      (ids) =>
        (ids as string[]).every(
          (id) => window.chessStudioEditor?.getShape(id as never) !== undefined,
        ),
      [noteA, noteB],
      { timeout: 15_000 },
    );
  }

  await a.context.close();
  await b.context.close();
});

test("an attendee cannot mutate authored structure or another attendee's shapes", async ({
  browser,
}) => {
  const a = await openAttendee(browser, `Ada-${Date.now()}`);
  const b = await openAttendee(browser, `Grace-${Date.now()}`);

  const noteA = `shape:e2e-own-${Date.now()}`;
  await createNote(a.page, noteA, 4600, 100);
  await b.page.waitForFunction(
    (id) => window.chessStudioEditor?.getShape(id as never) !== undefined,
    noteA,
    { timeout: 15_000 },
  );

  // B attacks the deck panel, a page, and A's note. Every mutation is
  // reverted by the ownership side effects before it can sync.
  const results = await b.page.evaluate((otherNote) => {
    const editor = window.chessStudioEditor;
    if (!editor) throw new Error("no editor");
    editor.deleteShape("shape:deck-panel" as never);
    const before = editor.getShape(otherNote as never);
    editor.updateShape({ id: otherNote as never, type: "note", x: 9999 });
    editor.deletePage("page:board-sound" as never);
    return {
      deckSurvives: editor.getShape("shape:deck-panel" as never) !== undefined,
      otherNoteX: editor.getShape(otherNote as never)?.x,
      otherNoteBeforeX: before?.x,
      pageCount: editor.getPages().length,
    };
  }, noteA);

  expect(results.deckSurvives).toBe(true);
  expect(results.otherNoteX).toBe(results.otherNoteBeforeX);
  expect(results.pageCount).toBe(5);

  // Nothing leaked to A either.
  await a.page.waitForTimeout(1500);
  expect(await hasShape(a.page, "shape:deck-panel")).toBe(true);
  expect(await hasShape(a.page, noteA)).toBe(true);

  // Sanity: B still owns their own edits.
  const noteB = `shape:e2e-mine-${Date.now()}`;
  await createNote(b.page, noteB, 4900, 100);
  expect(await hasShape(b.page, noteB)).toBe(true);
  await b.page.evaluate((id) => {
    window.chessStudioEditor?.deleteShape(id as never);
  }, noteB);
  expect(await hasShape(b.page, noteB)).toBe(false);

  await a.context.close();
  await b.context.close();
});

test("presenter navigation moves an existing attendee and a late joiner to the same target, then send-to-workspace releases them", async ({
  browser,
}) => {
  const presenterContext = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
  const presenter = await presenterContext.newPage();
  await presenter.goto("/?presenter=1");
  await presenter.waitForSelector("#join-name");
  await presenter.fill("#join-name", "Presenter");
  await presenter.click('button[type="submit"]');
  await presenter.waitForFunction(() => window.chessStudioEditor !== undefined);

  const attendee = await openAttendee(browser, `Ada-${Date.now()}`);

  // Presenter moves to the presentation page and brings the room along.
  await presenter.click('[data-testid="page-tab-presentation"]');
  await presenter.click("text=Bring everyone to presenter view");
  // Slide stepping only broadcasts while the client knows presenter
  // mode is active; wait for that state to land before using Next.
  await expect(presenter.locator('[data-presenter-mode="presenter"]')).toBeVisible({
    timeout: 10_000,
  });

  await attendee.page.waitForFunction(
    () => window.chessStudioEditor?.getCurrentPageId() === "page:presentation",
    undefined,
    { timeout: 10_000 },
  );

  // Prev/Next in presenter mode broadcasts the frame target.
  await presenter.click('[data-testid="slide-controls"] button:has-text("Next")');
  // The broadcast is server-side truth; require it before checking
  // that anyone followed.
  await expect
    .poll(
      async () => {
        const response = await presenter.request.get("/api/presenter");
        const state = (await response.json()) as { target_frame_id: string | null };
        return state.target_frame_id;
      },
      { timeout: 10_000 },
    )
    .not.toBeNull();
  // Let the 250ms zoom animation settle before treating the
  // presenter's viewport as the reference.
  await presenter.waitForTimeout(700);
  const presenterView = await presenter.evaluate(() =>
    window.chessStudioEditor?.getViewportPageBounds(),
  );

  const attendeeFollowed = async (page: Page) => {
    await page.waitForFunction(
      (view) => {
        const editor = window.chessStudioEditor;
        if (editor?.getCurrentPageId() !== "page:presentation") return false;
        const mine = editor.getViewportPageBounds();
        const target = view as { x: number; y: number; w: number; h: number };
        // Same region of the canvas: centers within half a slide of
        // each other (viewport aspect ratios differ per machine).
        const dx = Math.abs(mine.x + mine.w / 2 - (target.x + target.w / 2));
        const dy = Math.abs(mine.y + mine.h / 2 - (target.y + target.h / 2));
        return dx < 800 && dy < 450;
      },
      presenterView,
      { timeout: 15_000 },
    );
  };
  await attendeeFollowed(attendee.page);

  // A late joiner lands on the same frame from their first poll.
  const late = await openAttendee(browser, `Late-${Date.now()}`);
  await attendeeFollowed(late.page);

  // No overlap between the room panels after remote navigation, on a
  // projector-sized viewport (presenter) and the attendee defaults.
  for (const page of [presenter, attendee.page, late.page]) {
    const attendees = await page.locator(".attendee-panel").boundingBox();
    const controls = await page.locator('[data-testid="slide-controls"]').boundingBox();
    if (attendees && controls) {
      const overlaps =
        attendees.x < controls.x + controls.width &&
        controls.x < attendees.x + attendees.width &&
        attendees.y < controls.y + controls.height &&
        controls.y < attendees.y + attendees.height;
      expect(overlaps).toBe(false);
    }
  }

  // Send everyone back: both attendees end on their own workspace.
  await presenter.click("text=Send users to their workspace");
  for (const page of [attendee.page, late.page]) {
    await page.waitForFunction(
      () => window.chessStudioEditor?.getCurrentPageId() === "page:chess-machine",
      undefined,
      { timeout: 10_000 },
    );
    await expect(page.locator(".workspace-panel-own")).toBeAttached();
  }

  await presenterContext.close();
  await attendee.context.close();
  await late.context.close();
});

test("a narrow laptop viewport keeps the panels apart after remote navigation", async ({
  browser,
}) => {
  const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const page = await context.newPage();
  await joinAs(page, `Narrow-${Date.now()}`);

  const attendees = await page.locator(".attendee-panel").boundingBox();
  const controls = await page.locator('[data-testid="slide-controls"]').boundingBox();
  if (attendees && controls) {
    const overlaps =
      attendees.x < controls.x + controls.width &&
      controls.x < attendees.x + attendees.width &&
      attendees.y < controls.y + controls.height &&
      controls.y < attendees.y + attendees.height;
    expect(overlaps).toBe(false);
  }
  await context.close();
});
