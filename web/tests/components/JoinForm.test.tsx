import { afterEach, describe, expect, mock, test } from "bun:test";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { JoinResult } from "../../src/actions/joinWorkshop";
import { JoinForm } from "../../src/components/JoinForm";

function fakeEditor() {
  return {
    getShape: mock(() => undefined),
    createShape: mock(() => {}),
    updateShape: mock(() => {}),
    setCurrentPage: mock(() => {}),
    getShapePageBounds: mock(() => ({ x: 0, y: 0, w: 900, h: 560 })),
    zoomToBounds: mock(() => {}),
  };
}

function routedFetch() {
  return mock(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.endsWith("/users")) {
      return new Response(JSON.stringify({ id: "user_1", name: "Ada", created_at: "now" }), {
        status: 201,
      });
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
        { status: 201 },
      );
    }
    return new Response("not found", { status: 404 });
  }) as unknown as typeof fetch;
}

afterEach(() => {
  cleanup();
  localStorage.clear();
});

describe("JoinForm", () => {
  test("disables submit until the canvas has mounted", () => {
    render(<JoinForm editor={null} onJoined={() => {}} />);
    expect(screen.getByRole("button").hasAttribute("disabled")).toBe(true);
  });

  test("disables submit until a name is entered", () => {
    render(<JoinForm editor={fakeEditor() as never} onJoined={() => {}} />);
    expect(screen.getByRole("button").hasAttribute("disabled")).toBe(true);
  });

  test("joins and calls onJoined with the result", async () => {
    globalThis.fetch = routedFetch();
    const onJoined = mock((_result: JoinResult) => {});
    const editor = fakeEditor();
    render(<JoinForm editor={editor as never} onJoined={onJoined} />);

    fireEvent.change(screen.getByLabelText("Your name"), { target: { value: "Ada" } });
    fireEvent.click(screen.getByRole("button"));

    await waitFor(() => {
      expect(onJoined).toHaveBeenCalledTimes(1);
    });
    const [result] = onJoined.mock.calls[0];
    expect(result.user.name).toBe("Ada");
    expect(editor.createShape).toHaveBeenCalledTimes(1);
    expect(editor.setCurrentPage).toHaveBeenCalledTimes(1);
  });
});
