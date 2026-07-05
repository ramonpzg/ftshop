import { afterEach, describe, expect, mock, test } from "bun:test";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { PresenterPanel } from "../../src/components/presenter/PresenterPanel";

function makeEditor() {
  return {
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
  return mock(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.endsWith("/presenter") && !url.includes("bring") && !url.includes("send")) {
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
          active_page_slug: "presentation",
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
  }) as unknown as typeof fetch;
}

afterEach(() => {
  cleanup();
});

describe("PresenterPanel", () => {
  test("loads the lock state on mount", async () => {
    globalThis.fetch = routedFetch(false);
    const onLockedChange = mock((_locked: boolean) => {});
    render(
      <PresenterPanel
        editor={null}
        currentUser={null}
        onLockedChange={onLockedChange}
        onPageReset={() => {}}
      />,
    );

    await waitFor(() => {
      expect(onLockedChange).toHaveBeenCalledWith(false);
    });
    expect(screen.getByText("Lock editing")).toBeTruthy();
  });

  test("toggling lock calls the backend and notifies the parent", async () => {
    globalThis.fetch = routedFetch(false);
    const onLockedChange = mock((_locked: boolean) => {});
    render(
      <PresenterPanel
        editor={null}
        currentUser={null}
        onLockedChange={onLockedChange}
        onPageReset={() => {}}
      />,
    );

    await waitFor(() => screen.getByText("Lock editing"));
    fireEvent.click(screen.getByText("Lock editing"));

    await waitFor(() => {
      expect(screen.getByText("Unlock editing")).toBeTruthy();
    });
    expect(onLockedChange).toHaveBeenCalledWith(true);
  });

  test("bring to presenter view switches the editor's page", async () => {
    globalThis.fetch = routedFetch(false);
    const editor = makeEditor();
    render(
      <PresenterPanel
        editor={editor as never}
        currentUser={null}
        onLockedChange={() => {}}
        onPageReset={() => {}}
      />,
    );

    await waitFor(() => screen.getByText("Bring everyone to presenter view"));
    fireEvent.click(screen.getByText("Bring everyone to presenter view"));

    await waitFor(() => {
      expect(editor.setCurrentPage).toHaveBeenCalledTimes(1);
    });
  });

  test("reset page calls onPageReset", async () => {
    globalThis.fetch = routedFetch(false);
    const onPageReset = mock(() => {});
    render(
      <PresenterPanel
        editor={null}
        currentUser={null}
        onLockedChange={() => {}}
        onPageReset={onPageReset}
      />,
    );

    await waitFor(() => screen.getByText("Reset page"));
    fireEvent.click(screen.getByText("Reset page"));

    await waitFor(() => {
      expect(onPageReset).toHaveBeenCalledTimes(1);
    });
  });
});
