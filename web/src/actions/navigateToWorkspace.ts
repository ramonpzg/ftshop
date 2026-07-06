import type { Editor, TLShapeId } from "tldraw";
import type { Workspace } from "../data/api";
import { pageIdForSlug } from "./seedTldrawDocument";

/** Switches to a workspace's page and centers the camera on its shape.
 * Zoom caps at 100% so a large monitor doesn't blow the panel up. */
export function navigateToWorkspace(editor: Editor, workspace: Workspace, pageSlug: string): void {
  editor.setCurrentPage(pageIdForSlug(pageSlug));
  const bounds = editor.getShapePageBounds(workspace.shape_id as TLShapeId);
  if (bounds) {
    editor.zoomToBounds(bounds, { targetZoom: 1, animation: { duration: 300 } });
  }
}
