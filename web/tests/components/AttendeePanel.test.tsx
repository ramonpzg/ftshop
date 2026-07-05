import { afterEach, describe, expect, mock, test } from "bun:test";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { AttendeePanel } from "../../src/components/AttendeePanel";

const sampleWorkspace = {
  id: "workspace_1",
  user_id: "user_1",
  page_id: "page_1",
  shape_id: "shape:workspace-user_1-chess-machine",
  position_index: 0,
  selected_snippet_id: null,
  board_fen: "startpos",
  user_name: "Ada",
  page_slug: "chess-machine",
  page_title: "Building a Chess Machine",
};

function fetchReturning(body: unknown) {
  return mock(async () => new Response(JSON.stringify(body))) as unknown as typeof fetch;
}

afterEach(() => {
  cleanup();
});

describe("AttendeePanel", () => {
  test("lists attendees fetched from the backend", async () => {
    globalThis.fetch = fetchReturning([sampleWorkspace]);

    render(<AttendeePanel editor={null} currentUserId={null} refreshToken={0} />);

    await waitFor(() => {
      expect(screen.getByTestId("attendee-user_1")).toBeTruthy();
    });
    expect(screen.getByText("Ada")).toBeTruthy();
    expect(screen.getByText("Building a Chess Machine")).toBeTruthy();
  });

  test("clicking an attendee navigates the editor to their workspace", async () => {
    globalThis.fetch = fetchReturning([sampleWorkspace]);
    const editor = {
      getShape: mock(() => ({ id: "shape:workspace-user_1-chess-machine" })),
      createShape: mock(() => {}),
      updateShape: mock(() => {}),
      setCurrentPage: mock(() => {}),
      getShapePageBounds: mock(() => ({ x: 0, y: 0, w: 900, h: 560 })),
      zoomToBounds: mock(() => {}),
    };

    render(<AttendeePanel editor={editor as never} currentUserId={null} refreshToken={0} />);

    const button = await screen.findByTestId("attendee-user_1");
    button.click();

    expect(editor.setCurrentPage).toHaveBeenCalledTimes(1);
    expect(editor.zoomToBounds).toHaveBeenCalledTimes(1);
  });

  test("shows an empty state before anyone has joined", async () => {
    globalThis.fetch = fetchReturning([]);

    render(<AttendeePanel editor={null} currentUserId={null} refreshToken={0} />);

    await waitFor(() => {
      expect(screen.getByText("No one has joined yet.")).toBeTruthy();
    });
  });
});
