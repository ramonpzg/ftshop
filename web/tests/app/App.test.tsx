import { afterEach, describe, expect, mock, test } from "bun:test";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { App } from "../../src/app/App";

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
