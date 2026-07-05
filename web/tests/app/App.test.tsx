import { afterEach, beforeEach, describe, expect, mock, test } from "bun:test";
import { cleanup, render, screen, waitFor } from "@testing-library/react";

// The real canvas mounts a full tldraw Editor, which needs browser APIs
// (ResizeObserver, canvas contexts, IndexedDB persistence) that happy-dom
// doesn't implement. App-level tests only care about the backend status
// badge and top-level wiring, so the canvas is replaced with a stub.
mock.module("../../src/components/tldraw/ChessStudioCanvas", () => ({
  ChessStudioCanvas: () => null,
}));

const { App } = await import("../../src/app/App");

function routedFetch(healthStatus: number) {
  return mock(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.endsWith("/health")) {
      return healthStatus === 200
        ? new Response(JSON.stringify({ status: "ok" }))
        : new Response("boom", { status: healthStatus });
    }
    if (url.endsWith("/workspaces")) {
      return new Response(JSON.stringify([]));
    }
    if (url.endsWith("/presenter")) {
      return new Response(
        JSON.stringify({
          mode: "idle",
          locked: false,
          active_page_slug: null,
          focused_user_id: null,
          updated_at: "now",
        }),
      );
    }
    return new Response("not found", { status: 404 });
  }) as unknown as typeof fetch;
}

beforeEach(() => {
  localStorage.clear();
});

afterEach(() => {
  cleanup();
  mock.restore();
});

describe("App", () => {
  test("shows connected once the backend health check resolves", async () => {
    globalThis.fetch = routedFetch(200);

    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId("backend-status").textContent).toBe("Backend: connected");
    });
  });

  test("shows unreachable when the health check fails", async () => {
    globalThis.fetch = routedFetch(500);

    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId("backend-status").textContent).toBe("Backend: unreachable");
    });
  });

  test("shows the join form when no local user is stored", async () => {
    globalThis.fetch = routedFetch(200);

    render(<App />);

    await waitFor(() => {
      expect(screen.getByLabelText("Your name")).toBeTruthy();
    });
  });
});
