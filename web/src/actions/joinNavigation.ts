/** Decides where a joining client's camera goes.
 *
 * While the presenter is driving the room, joining must not yank the
 * camera to the workspace: the presenter target has already been (or
 * is about to be) applied, and the revision that carried it will not
 * repeat. Only a successful presenter-state read can settle that, so
 * failures retry until an answer arrives or the caller cancels.
 *
 * Retrying forever is deliberate. The presenter poll cannot stand in
 * for this decision: its first successful read of an idle room applies
 * nothing by design, so giving up here would leave the attendee
 * wherever the camera happened to be for the rest of the session. The
 * loop only ends with an answer or with the effect that started it.
 */

import { fetchPresenterState } from "../data/api";

export type JoinNavigation = "workspace" | "stay";

export interface JoinNavigationOptions {
  /** Retry budget, for tests. The default retries until cancelled. */
  attempts?: number;
  delayMs?: number;
  isCancelled?: () => boolean;
}

export async function resolveJoinNavigation(
  options: JoinNavigationOptions = {},
): Promise<JoinNavigation> {
  const attempts = options.attempts ?? Number.POSITIVE_INFINITY;
  const delayMs = options.delayMs ?? 1000;
  const isCancelled = options.isCancelled ?? (() => false);

  for (let attempt = 0; attempt < attempts; attempt++) {
    if (isCancelled()) return "stay";
    const state = await fetchPresenterState().catch(() => null);
    if (isCancelled()) return "stay";
    if (state !== null) {
      return state.mode === "presenter" ? "stay" : "workspace";
    }
    await new Promise((resolve) => setTimeout(resolve, delayMs));
  }
  return "stay";
}
