import { afterEach, describe, expect, mock, test } from "bun:test";
import { cleanup, render, screen, waitFor } from "@testing-library/react";

// The real canvas mounts a full tldraw Editor, which needs browser APIs
// (ResizeObserver, canvas contexts, IndexedDB persistence) that happy-dom
// doesn't implement. App-level tests only care about the backend status
// badge, so the canvas is replaced with a stub.
mock.module("../../src/components/tldraw/ChessStudioCanvas", () => ({
  ChessStudioCanvas: () => null,
}));

const { App } = await import("../../src/app/App");

afterEach(() => {
  cleanup();
  mock.restore();
});

describe("App", () => {
  test("shows connected once the backend health check resolves", async () => {
    globalThis.fetch = mock(
      async () => new Response(JSON.stringify({ status: "ok" })),
    ) as unknown as typeof fetch;

    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId("backend-status").textContent).toBe("Backend: connected");
    });
  });

  test("shows unreachable when the health check fails", async () => {
    globalThis.fetch = mock(
      async () => new Response("boom", { status: 500 }),
    ) as unknown as typeof fetch;

    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId("backend-status").textContent).toBe("Backend: unreachable");
    });
  });
});
