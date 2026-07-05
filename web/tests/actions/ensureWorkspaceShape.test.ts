import { describe, expect, mock, test } from "bun:test";
import { ensureWorkspaceShape } from "../../src/actions/ensureWorkspaceShape";
import type { Workspace } from "../../src/data/api";

function makeWorkspace(overrides: Partial<Workspace> = {}): Workspace {
  return {
    id: "workspace_1",
    user_id: "user_1",
    page_id: "page_1",
    shape_id: "shape:workspace-user_1-chess-machine",
    position_index: 0,
    selected_snippet_id: null,
    board_fen: "startpos",
    ...overrides,
  };
}

interface ShapePartial {
  id: string;
  type: string;
  x?: number;
  y?: number;
  props: { userName: string; [key: string]: unknown };
}

function makeFakeEditor(existingShape: unknown) {
  return {
    getShape: mock(() => existingShape),
    createShape: mock((_shape: ShapePartial) => {}),
    updateShape: mock((_shape: ShapePartial) => {}),
  };
}

describe("ensureWorkspaceShape", () => {
  test("creates a shape when none exists yet", () => {
    const editor = makeFakeEditor(undefined);
    const workspace = makeWorkspace();

    ensureWorkspaceShape(editor as never, workspace, "Ada", "chess-machine");

    expect(editor.createShape).toHaveBeenCalledTimes(1);
    expect(editor.updateShape).not.toHaveBeenCalled();
    const [created] = editor.createShape.mock.calls[0];
    expect(created.id).toBe(workspace.shape_id);
    expect(created.type).toBe("workspace");
    expect(created.props.userName).toBe("Ada");
  });

  test("positions the first workspace at the left edge, below the seed content", () => {
    const editor = makeFakeEditor(undefined);
    ensureWorkspaceShape(
      editor as never,
      makeWorkspace({ position_index: 0 }),
      "Ada",
      "chess-machine",
    );
    const [created] = editor.createShape.mock.calls[0];
    expect(created.x).toBe(0);
    expect(created.y).toBeGreaterThan(800);
  });

  test("updates the display name when the shape already exists", () => {
    const editor = makeFakeEditor({ id: "shape:workspace-user_1-chess-machine" });
    const workspace = makeWorkspace();

    ensureWorkspaceShape(editor as never, workspace, "Ada Renamed", "chess-machine");

    expect(editor.createShape).not.toHaveBeenCalled();
    expect(editor.updateShape).toHaveBeenCalledTimes(1);
    const [updated] = editor.updateShape.mock.calls[0];
    expect(updated.props.userName).toBe("Ada Renamed");
  });
});
