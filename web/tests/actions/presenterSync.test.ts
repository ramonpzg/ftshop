import { afterEach, describe, expect, mock, test } from "bun:test";
import { startPresenterSync } from "../../src/actions/presenterSync";

function wait(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

interface EditorMock {
  readonly: boolean;
  currentPage: string;
  zoomedTo: unknown[];
  getIsReadonly: () => boolean;
  updateInstanceState: (partial: { isReadonly?: boolean }) => void;
  setCurrentPage: (id: string) => void;
  zoomToFit: () => void;
  getPages: () => Array<{ id: string }>;
  getShape: (id: string) => { id: string } | undefined;
  getAncestorPageId: (shape: { id: string }) => string;
  getShapePageBounds: (id: string) => { x: number; y: number; w: number; h: number } | undefined;
  zoomToBounds: (bounds: unknown, opts?: unknown) => void;
}

function makeEditor(options: { frameExists?: boolean } = {}): EditorMock {
  const editor: EditorMock = {
    readonly: false,
    currentPage: "page:presentation",
    zoomedTo: [],
    getIsReadonly: () => editor.readonly,
    updateInstanceState: (partial) => {
      if (partial.isReadonly !== undefined) editor.readonly = partial.isReadonly;
    },
    setCurrentPage: (id: string) => {
      editor.currentPage = id;
    },
    zoomToFit: mock(() => {}),
    getPages: () => [
      { id: "page:presentation" },
      { id: "page:chess-machine" },
      { id: "page:board-sound" },
    ],
    getShape: (id: string) => (options.frameExists ? { id } : undefined),
    getAncestorPageId: () => "page:board-sound",
    getShapePageBounds: () => ({ x: 10, y: 20, w: 1600, h: 900 }),
    zoomToBounds: mock((bounds: unknown) => {
      editor.zoomedTo.push(bounds);
    }),
  };
  return editor;
}

function presenterStateFetch(states: Array<Record<string, unknown>>) {
  let index = 0;
  return mock(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.endsWith("/presenter")) {
      const state = states[Math.min(index, states.length - 1)];
      index += 1;
      return new Response(JSON.stringify(state));
    }
    return new Response("not found", { status: 404 });
  }) as unknown as typeof fetch;
}

const baseState = {
  mode: "idle",
  locked: false,
  active_page_slug: null,
  focused_user_id: null,
  updated_at: "t0",
  revision: 0,
  target_frame_id: null,
  target_bounds: null,
};

afterEach(() => {
  mock.restore();
});

describe("startPresenterSync", () => {
  test("applies the lock to attendees but never to the presenter", async () => {
    globalThis.fetch = presenterStateFetch([{ ...baseState, locked: true, revision: 1 }]);
    const attendee = makeEditor();
    const onLockedChange = mock((_locked: boolean) => {});
    const stopA = startPresenterSync({
      editor: attendee as never,
      isPresenter: false,
      getCurrentUserId: () => null,
      onLockedChange,
      intervalMs: 10_000,
    });
    await wait(20);
    expect(attendee.readonly).toBe(true);
    expect(onLockedChange).toHaveBeenCalledWith(true);
    stopA();

    globalThis.fetch = presenterStateFetch([{ ...baseState, locked: true, revision: 1 }]);
    const presenter = makeEditor();
    const stopB = startPresenterSync({
      editor: presenter as never,
      isPresenter: true,
      getCurrentUserId: () => null,
      onLockedChange: () => {},
      intervalMs: 10_000,
    });
    await wait(20);
    expect(presenter.readonly).toBe(false);
    stopB();
  });

  test("moves attendees when a newer revision arrives", async () => {
    globalThis.fetch = presenterStateFetch([
      baseState,
      { ...baseState, mode: "presenter", active_page_slug: "board-sound", revision: 1 },
    ]);
    const attendee = makeEditor();
    const stop = startPresenterSync({
      editor: attendee as never,
      isPresenter: false,
      getCurrentUserId: () => null,
      onLockedChange: () => {},
      intervalMs: 15,
    });
    await wait(80);
    expect(attendee.currentPage).toBe("page:board-sound");
    stop();
  });

  test("a late joiner is brought to the current presenter target on the first poll", async () => {
    globalThis.fetch = presenterStateFetch([
      {
        ...baseState,
        mode: "presenter",
        active_page_slug: "board-sound",
        revision: 7,
        target_bounds: { x: 0, y: 0, w: 800, h: 600 },
      },
    ]);
    const lateJoiner = makeEditor();
    const stop = startPresenterSync({
      editor: lateJoiner as never,
      isPresenter: false,
      getCurrentUserId: () => null,
      onLockedChange: () => {},
      intervalMs: 10_000,
    });
    await wait(30);
    expect(lateJoiner.currentPage).toBe("page:board-sound");
    expect(lateJoiner.zoomedTo).toHaveLength(1);
    stop();
  });

  test("an idle room leaves a fresh client where it is", async () => {
    globalThis.fetch = presenterStateFetch([baseState]);
    const attendee = makeEditor();
    const stop = startPresenterSync({
      editor: attendee as never,
      isPresenter: false,
      getCurrentUserId: () => null,
      onLockedChange: () => {},
      intervalMs: 10_000,
    });
    await wait(30);
    expect(attendee.currentPage).toBe("page:presentation");
    stop();
  });

  test("repeated polls with the same revision do not re-apply the camera", async () => {
    const driven = {
      ...baseState,
      mode: "presenter",
      active_page_slug: "board-sound",
      revision: 3,
      target_bounds: { x: 0, y: 0, w: 800, h: 600 },
    };
    globalThis.fetch = presenterStateFetch([driven, driven, driven]);
    const attendee = makeEditor();
    const stop = startPresenterSync({
      editor: attendee as never,
      isPresenter: false,
      getCurrentUserId: () => null,
      onLockedChange: () => {},
      intervalMs: 10,
    });
    await wait(80);
    expect(attendee.zoomedTo).toHaveLength(1);
    stop();
  });

  test("an older revision arriving late never rolls the camera back", async () => {
    globalThis.fetch = presenterStateFetch([
      {
        ...baseState,
        mode: "presenter",
        active_page_slug: "board-sound",
        revision: 9,
        target_bounds: { x: 0, y: 0, w: 800, h: 600 },
      },
      {
        ...baseState,
        mode: "presenter",
        active_page_slug: "chess-machine",
        revision: 4,
        target_bounds: { x: 5, y: 5, w: 100, h: 100 },
      },
    ]);
    const attendee = makeEditor();
    const stop = startPresenterSync({
      editor: attendee as never,
      isPresenter: false,
      getCurrentUserId: () => null,
      onLockedChange: () => {},
      intervalMs: 10,
    });
    await wait(60);
    expect(attendee.currentPage).toBe("page:board-sound");
    expect(attendee.zoomedTo).toHaveLength(1);
    stop();
  });

  test("a deleted frame degrades to a page view and reports a concise notice", async () => {
    globalThis.fetch = presenterStateFetch([
      {
        ...baseState,
        mode: "presenter",
        active_page_slug: "board-sound",
        revision: 2,
        target_frame_id: "shape:gone",
      },
    ]);
    const attendee = makeEditor({ frameExists: false });
    const notices: string[] = [];
    const stop = startPresenterSync({
      editor: attendee as never,
      isPresenter: false,
      getCurrentUserId: () => null,
      onLockedChange: () => {},
      onNotice: (notice) => notices.push(notice),
      intervalMs: 10_000,
    });
    await wait(30);
    expect(attendee.currentPage).toBe("page:board-sound");
    expect(notices).toEqual(["Presenter frame missing. Showing the page."]);
    stop();
  });

  test("never drives the presenter's own camera", async () => {
    globalThis.fetch = presenterStateFetch([
      baseState,
      { ...baseState, mode: "presenter", active_page_slug: "board-sound", revision: 1 },
    ]);
    const presenter = makeEditor();
    const stop = startPresenterSync({
      editor: presenter as never,
      isPresenter: true,
      getCurrentUserId: () => null,
      onLockedChange: () => {},
      intervalMs: 15,
    });
    await wait(60);
    expect(presenter.currentPage).toBe("page:presentation");
    stop();
  });
});

test("a failed workspace lookup does not consume the revision; the next poll retries", async () => {
  let workspaceCalls = 0;
  globalThis.fetch = mock(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.endsWith("/presenter")) {
      return new Response(JSON.stringify({ ...baseState, mode: "workspaces", revision: 5 }));
    }
    if (url.endsWith("/workspaces")) {
      workspaceCalls += 1;
      if (workspaceCalls === 1) return new Response("boom", { status: 500 });
      return new Response(
        JSON.stringify({
          id: "ws1",
          user_id: "u1",
          page_id: "p1",
          shape_id: "shape:workspace-u1-chess-machine",
          position_index: 0,
          selected_snippet_id: null,
          board_fen: "startpos",
        }),
      );
    }
    return new Response("not found", { status: 404 });
  }) as unknown as typeof fetch;

  const attendee = makeEditor();
  const stop = startPresenterSync({
    editor: attendee as never,
    isPresenter: false,
    getCurrentUserId: () => "u1",
    onLockedChange: () => {},
    intervalMs: 15,
  });
  await wait(120);
  // The transient 500 left revision 5 unconsumed, so a later poll
  // retried it and this attendee still reached their workspace.
  expect(workspaceCalls).toBeGreaterThanOrEqual(2);
  expect(attendee.currentPage).toBe("page:chess-machine");
  stop();
});
