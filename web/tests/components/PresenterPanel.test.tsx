import { afterEach, describe, expect, mock, test } from "bun:test";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { PresenterPanel } from "../../src/components/presenter/PresenterPanel";

function makeEditor() {
  return {
    getCurrentPageId: mock(() => "page:board-sound"),
    setCurrentPage: mock(() => {}),
    getShape: mock(() => undefined),
    createShape: mock(() => {}),
    updateShape: mock(() => {}),
    getShapePageBounds: mock(() => ({ x: 0, y: 0, w: 900, h: 560 })),
    zoomToBounds: mock(() => {}),
  };
}

function routedFetch(initialLocked: boolean) {
  let locked = initialLocked;
  const calls: string[] = [];
  const fetchMock = mock(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    calls.push(`${init?.method ?? "GET"} ${url}${init?.body ? ` ${init.body}` : ""}`);
    if (url.endsWith("/presenter/lock") || url.endsWith("/presenter/unlock")) {
      locked = url.endsWith("/lock");
      return new Response(
        JSON.stringify({
          mode: "idle",
          locked,
          active_page_slug: null,
          focused_user_id: null,
          updated_at: "now",
        }),
      );
    }
    if (url.endsWith("/bring-to-presenter-view")) {
      return new Response(
        JSON.stringify({
          mode: "presenter",
          locked,
          active_page_slug: "board-sound",
          focused_user_id: null,
          updated_at: "now",
        }),
      );
    }
    if (url.endsWith("/send-to-workspaces")) {
      return new Response(
        JSON.stringify({
          mode: "workspaces",
          locked,
          active_page_slug: null,
          focused_user_id: null,
          updated_at: "now",
        }),
      );
    }
    if (url.endsWith("/reset-page")) {
      return new Response(JSON.stringify({ workspaces_reset: 1 }));
    }
    if (url.endsWith("/workspaces")) {
      return new Response(
        JSON.stringify({
          id: "workspace_1",
          user_id: "user_1",
          page_id: "page_1",
          shape_id: "shape:workspace-user_1-chess-machine",
          position_index: 0,
          selected_snippet_id: null,
          board_fen: "startpos",
        }),
      );
    }
    return new Response("not found", { status: 404 });
  }) as unknown as typeof fetch & { mock: { calls: unknown[] } };
  return { fetchMock, calls };
}

afterEach(() => {
  cleanup();
});

describe("PresenterPanel", () => {
  test("shows the lock action matching the locked prop", () => {
    const { fetchMock } = routedFetch(false);
    globalThis.fetch = fetchMock;
    render(
      <PresenterPanel
        editor={null}
        currentUser={null}
        locked={false}
        onLockedChange={() => {}}
        onPageReset={() => {}}
      />,
    );
    expect(screen.getByText("Lock editing")).toBeTruthy();
    cleanup();
    render(
      <PresenterPanel
        editor={null}
        currentUser={null}
        locked={true}
        onLockedChange={() => {}}
        onPageReset={() => {}}
      />,
    );
    expect(screen.getByText("Unlock editing")).toBeTruthy();
  });

  test("toggling lock calls the backend and notifies the parent", async () => {
    const { fetchMock } = routedFetch(false);
    globalThis.fetch = fetchMock;
    const onLockedChange = mock((_locked: boolean) => {});
    render(
      <PresenterPanel
        editor={null}
        currentUser={null}
        locked={false}
        onLockedChange={onLockedChange}
        onPageReset={() => {}}
      />,
    );

    fireEvent.click(screen.getByText("Lock editing"));

    await waitFor(() => {
      expect(onLockedChange).toHaveBeenCalledWith(true);
    });
  });

  test("bring to presenter view broadcasts the presenter's current page", async () => {
    const { fetchMock, calls } = routedFetch(false);
    globalThis.fetch = fetchMock;
    const editor = makeEditor();
    render(
      <PresenterPanel
        editor={editor as never}
        currentUser={null}
        locked={false}
        onLockedChange={() => {}}
        onPageReset={() => {}}
      />,
    );

    fireEvent.click(screen.getByText("Bring everyone to presenter view"));

    await waitFor(() => {
      expect(editor.setCurrentPage).toHaveBeenCalledTimes(1);
    });
    const bringCall = calls.find((c) => c.includes("bring-to-presenter-view"));
    expect(bringCall).toContain("board-sound");
  });

  test("reset page asks for confirmation before wiping games", async () => {
    const { fetchMock } = routedFetch(false);
    globalThis.fetch = fetchMock;
    const onPageReset = mock(() => {});

    const originalConfirm = window.confirm;
    window.confirm = mock(() => false) as typeof window.confirm;
    render(
      <PresenterPanel
        editor={null}
        currentUser={null}
        locked={false}
        onLockedChange={() => {}}
        onPageReset={onPageReset}
      />,
    );
    fireEvent.click(screen.getByText("Reset page"));
    expect(onPageReset).toHaveBeenCalledTimes(0);

    window.confirm = mock(() => true) as typeof window.confirm;
    fireEvent.click(screen.getByText("Reset page"));
    await waitFor(() => {
      expect(onPageReset).toHaveBeenCalledTimes(1);
    });
    window.confirm = originalConfirm;
  });
});
