import { afterEach, describe, expect, mock, test } from "bun:test";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { JoinResult } from "../../src/actions/joinWorkshop";
import { JoinForm } from "../../src/components/JoinForm";

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
  test("disables submit until the room has connected", () => {
    render(<JoinForm ready={false} onJoined={() => {}} />);
    expect(screen.getByRole("button").hasAttribute("disabled")).toBe(true);
  });

  test("disables submit until a name is entered", () => {
    render(<JoinForm ready onJoined={() => {}} />);
    expect(screen.getByRole("button").hasAttribute("disabled")).toBe(true);
  });

  test("joins, saves the local user, and calls onJoined with the result", async () => {
    globalThis.fetch = routedFetch();
    const onJoined = mock((_result: JoinResult) => {});
    render(<JoinForm ready onJoined={onJoined} />);

    fireEvent.change(screen.getByLabelText("Your name"), { target: { value: "Ada" } });
    fireEvent.click(screen.getByRole("button"));

    await waitFor(() => {
      expect(onJoined).toHaveBeenCalledTimes(1);
    });
    const [result] = onJoined.mock.calls[0];
    expect(result.user.name).toBe("Ada");
    expect(result.workspace.shape_id).toBe("shape:workspace-user_1-chess-machine");
    // The shape itself is created after the room reconnects with the new
    // identity, not here; joining only registers and remembers the user.
    expect(localStorage.getItem("euro-chess-studio:current-user")).toContain("user_1");
  });
});
