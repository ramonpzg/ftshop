/** Decides where a joining client's camera goes.
 *
 * While the presenter is driving the room, joining must not yank the
 * camera to the workspace: the presenter target has already been (or
 * is about to be) applied, and the revision that carried it will not
 * repeat. Only a successful presenter-state read can settle that, so a
 * failed request is retried rather than treated as permission. If the
 * backend stays unreachable past the retry budget, the safe answer is
 * to stay put: the presenter poll takes over navigation as soon as the
 * backend returns.
 */

import { fetchPresenterState } from "../data/api";

export type JoinNavigation = "workspace" | "stay";

export interface JoinNavigationOptions {
  attempts?: number;
  delayMs?: number;
  isCancelled?: () => boolean;
}

export async function resolveJoinNavigation(
  options: JoinNavigationOptions = {},
): Promise<JoinNavigation> {
  const attempts = options.attempts ?? 10;
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
