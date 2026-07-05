import type { Editor, TLShapeId } from "tldraw";
import { computeWorkspacePosition } from "../calculations/layout";
import type { Workspace } from "../data/api";
import { pageIdForSlug } from "./seedTldrawDocument";

/**
 * Creates the tldraw shape for a workspace the first time it's seen on this
 * client, or refreshes its display name if it already exists. Safe to call
 * on every join and every attendee-panel render.
 */
export function ensureWorkspaceShape(
  editor: Editor,
  workspace: Workspace,
  userName: string,
  pageSlug: string,
): void {
  const shapeId = workspace.shape_id as TLShapeId;
  const pageId = pageIdForSlug(pageSlug);
  const existing = editor.getShape(shapeId);
  const { x, y } = computeWorkspacePosition(workspace.position_index);

  if (!existing) {
    editor.createShape({
      id: shapeId,
      type: "workspace",
      parentId: pageId,
      x,
      y,
      props: {
        workspaceId: workspace.id,
        userId: workspace.user_id,
        userName,
        pageSlug,
      },
    });
    return;
  }

  editor.updateShape({
    id: shapeId,
    type: "workspace",
    props: { userName },
  });
}
