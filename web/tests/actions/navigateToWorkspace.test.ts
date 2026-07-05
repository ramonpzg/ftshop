import { describe, expect, mock, test } from "bun:test";
import { navigateToWorkspace } from "../../src/actions/navigateToWorkspace";
import type { Workspace } from "../../src/data/api";

function makeWorkspace(): Workspace {
  return {
    id: "workspace_1",
    user_id: "user_1",
    page_id: "page_1",
    shape_id: "shape:workspace-user_1-chess-machine",
    position_index: 0,
    selected_snippet_id: null,
    board_fen: "startpos",
  };
}

describe("navigateToWorkspace", () => {
  test("switches to the workspace's page and zooms to its shape", () => {
    const editor = {
      setCurrentPage: mock(() => {}),
      getShapePageBounds: mock(() => ({ x: 0, y: 0, w: 900, h: 560 })),
      zoomToBounds: mock(() => {}),
    };

    navigateToWorkspace(editor as never, makeWorkspace(), "chess-machine");

    expect(editor.setCurrentPage).toHaveBeenCalledTimes(1);
    expect(editor.zoomToBounds).toHaveBeenCalledTimes(1);
  });

  test("does not zoom when the shape isn't on the canvas yet", () => {
    const editor = {
      setCurrentPage: mock(() => {}),
      getShapePageBounds: mock(() => undefined),
      zoomToBounds: mock(() => {}),
    };

    navigateToWorkspace(editor as never, makeWorkspace(), "chess-machine");

    expect(editor.setCurrentPage).toHaveBeenCalledTimes(1);
    expect(editor.zoomToBounds).not.toHaveBeenCalled();
  });
});
