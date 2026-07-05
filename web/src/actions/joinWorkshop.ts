import type { Editor, TLShapeId } from "tldraw";
import { createOrGetWorkspace, createUser, type User, type Workspace } from "../data/api";
import { saveLocalUser } from "../data/localUser";
import { ensureWorkspaceShape } from "./ensureWorkspaceShape";
import { pageIdForSlug } from "./seedTldrawDocument";

/** New attendees land on the main technical page, where the interactive board lives. */
export const PRIMARY_WORKSPACE_PAGE_SLUG = "chess-machine";

export interface JoinResult {
  user: User;
  workspace: Workspace;
}

export async function joinWorkshop(editor: Editor, name: string): Promise<JoinResult> {
  const user = await createUser(name);
  const workspace = await createOrGetWorkspace(user.id, PRIMARY_WORKSPACE_PAGE_SLUG);
  saveLocalUser({ id: user.id, name: user.name });

  ensureWorkspaceShape(editor, workspace, user.name, PRIMARY_WORKSPACE_PAGE_SLUG);
  editor.setCurrentPage(pageIdForSlug(PRIMARY_WORKSPACE_PAGE_SLUG));

  const bounds = editor.getShapePageBounds(workspace.shape_id as TLShapeId);
  if (bounds) {
    editor.zoomToBounds(bounds, { animation: { duration: 300 } });
  }

  return { user, workspace };
}
