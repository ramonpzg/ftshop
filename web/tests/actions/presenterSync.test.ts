import { afterEach, describe, expect, mock, test } from "bun:test";
import { startPresenterSync } from "../../src/actions/presenterSync";

function wait(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

interface EditorMock {
  readonly: boolean;
  currentPage: string;
  getIsReadonly: () => boolean;
  updateInstanceState: (partial: { isReadonly?: boolean }) => void;
  setCurrentPage: (id: string) => void;
  zoomToFit: () => void;
  getShapePageBounds: () => { x: number; y: number; w: number; h: number };
  zoomToBounds: () => void;
}

function makeEditor(): EditorMock {
  const editor: EditorMock = {
    readonly: false,
    currentPage: "page:presentation",
    getIsReadonly: () => editor.readonly,
    updateInstanceState: (partial) => {
      if (partial.isReadonly !== undefined) editor.readonly = partial.isReadonly;
    },
    setCurrentPage: mock((id: string) => {
      editor.currentPage = id;
    }) as unknown as EditorMock["setCurrentPage"],
    zoomToFit: mock(() => {}),
    getShapePageBounds: () => ({ x: 0, y: 0, w: 900, h: 560 }),
    zoomToBounds: mock(() => {}),
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
};

afterEach(() => {
  mock.restore();
});

describe("startPresenterSync", () => {
  test("applies the lock to attendees but never to the presenter", async () => {
    globalThis.fetch = presenterStateFetch([{ ...baseState, locked: true }]);
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

    globalThis.fetch = presenterStateFetch([{ ...baseState, locked: true }]);
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

  test("moves attendees to the presenter's page when the state changes", async () => {
    globalThis.fetch = presenterStateFetch([
      baseState,
      { ...baseState, mode: "presenter", active_page_slug: "board-sound", updated_at: "t1" },
    ]);
    const attendee = makeEditor();
    const stop = startPresenterSync({
      editor: attendee as never,
      isPresenter: false,
      getCurrentUserId: () => null,
      onLockedChange: () => {},
      intervalMs: 15,
    });
    await wait(60);
    expect(attendee.currentPage).toBe("page:board-sound");
    stop();
  });

  test("does not yank the camera on the first poll", async () => {
    globalThis.fetch = presenterStateFetch([
      { ...baseState, mode: "presenter", active_page_slug: "board-sound" },
    ]);
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

  test("never drives the presenter's own camera", async () => {
    globalThis.fetch = presenterStateFetch([
      baseState,
      { ...baseState, mode: "presenter", active_page_slug: "board-sound", updated_at: "t1" },
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
