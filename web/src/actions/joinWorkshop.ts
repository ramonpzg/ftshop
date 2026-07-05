import type { Editor } from "tldraw";
import { createOrGetWorkspace, createUser, type User, type Workspace } from "../data/api";
import { saveLocalUser } from "../data/localUser";
import { ensureWorkspaceShape } from "./ensureWorkspaceShape";
import { navigateToWorkspace } from "./navigateToWorkspace";

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
  navigateToWorkspace(editor, workspace, PRIMARY_WORKSPACE_PAGE_SLUG);

  return { user, workspace };
}
