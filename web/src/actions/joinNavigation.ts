/** Decides where a joining client's camera goes.
 *
 * While the presenter is driving the room, joining must not yank the
 * camera to the workspace: the presenter target has already been (or
 * is about to be) applied, and the revision that carried it will not
 * repeat. Only a successful presenter-state read can settle that, so
 * failures retry until an answer arrives or the caller aborts.
 *
 * Retrying forever is deliberate. The presenter poll cannot stand in
 * for this decision: its first successful read of an idle room applies
 * nothing by design, so giving up here would leave the attendee
 * wherever the camera happened to be for the rest of the session.
 *
 * Every attempt runs under its own bounded timeout and is wired to the
 * caller's abort signal, so a stalled request neither freezes the loop
 * nor outlives the effect that started it.
 */

import { fetchPresenterState, type PresenterState } from "../data/api";

export type JoinNavigation = "workspace" | "stay";

export interface JoinNavigationOptions {
  /** Aborting ends the loop and any in-flight request. */
  signal?: AbortSignal;
  /** Retry budget, for tests. The default retries until aborted. */
  attempts?: number;
  delayMs?: number;
  /** Upper bound for a single presenter-state request. */
  requestTimeoutMs?: number;
}

async function fetchStateOnce(
  timeoutMs: number,
  outerSignal?: AbortSignal,
): Promise<PresenterState | null> {
  const controller = new AbortController();
  const abort = () => controller.abort();
  const timer = setTimeout(abort, timeoutMs);
  outerSignal?.addEventListener("abort", abort);
  if (outerSignal?.aborted) controller.abort();
  try {
    return await fetchPresenterState(controller.signal);
  } catch {
    return null;
  } finally {
    clearTimeout(timer);
    outerSignal?.removeEventListener("abort", abort);
  }
}

export async function resolveJoinNavigation(
  options: JoinNavigationOptions = {},
): Promise<JoinNavigation> {
  const attempts = options.attempts ?? Number.POSITIVE_INFINITY;
  const delayMs = options.delayMs ?? 1000;
  const requestTimeoutMs = options.requestTimeoutMs ?? 4000;
  const signal = options.signal;

  for (let attempt = 0; attempt < attempts; attempt++) {
    if (signal?.aborted) return "stay";
    const state = await fetchStateOnce(requestTimeoutMs, signal);
    if (signal?.aborted) return "stay";
    if (state !== null) {
      return state.mode === "presenter" ? "stay" : "workspace";
    }
    await new Promise((resolve) => setTimeout(resolve, delayMs));
  }
  return "stay";
}
