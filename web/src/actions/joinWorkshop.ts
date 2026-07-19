import { createOrGetWorkspace, createUser, type User, type Workspace } from "../data/api";
import { saveLocalUser } from "../data/localUser";

/** New attendees land on the main technical page, where the interactive board lives. */
export const PRIMARY_WORKSPACE_PAGE_SLUG = "chess-machine";

export interface JoinResult {
  user: User;
  workspace: Workspace;
}

/**
 * Registers the attendee with the backend and remembers them locally.
 * The workspace shape itself is created after the room reconnects with
 * the new identity (App's join effect), because the pre-join sync
 * session is read-only by design.
 */
export async function joinWorkshop(name: string): Promise<JoinResult> {
  const user = await createUser(name);
  const workspace = await createOrGetWorkspace(user.id, PRIMARY_WORKSPACE_PAGE_SLUG);
  saveLocalUser({ id: user.id, name: user.name });
  return { user, workspace };
}
