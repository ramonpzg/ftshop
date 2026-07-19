/** Pure connection-state machine for the deck's LiveRoom panel, kept
 * out of the Vue component so the states can be exercised in tests.
 *
 * Phases:
 * - connecting: no poll has completed yet.
 * - connected: the last poll succeeded; the data shown is fresh.
 * - recovering: a poll failed but earlier data exists; the stale list
 *   stays visible while retries continue.
 * - unavailable: polls fail and there is nothing to show.
 */

export interface RoomGamesPayload {
  games: Array<Record<string, unknown>>;
  playing: number;
  finished: number;
  total_dataset_rows: number;
}

export type LiveRoomPhase = "connecting" | "connected" | "recovering" | "unavailable";

export interface LiveRoomState {
  phase: LiveRoomPhase;
  room: RoomGamesPayload | null;
  /** Milliseconds timestamp of the last successful poll, for client-side
   * countdown interpolation between polls. */
  fetchedAt: number;
}

export const INITIAL_LIVE_ROOM_STATE: LiveRoomState = {
  phase: "connecting",
  room: null,
  fetchedAt: 0,
};

export type PollResult =
  | { ok: true; room: RoomGamesPayload; at: number }
  | { ok: false };

export function applyPollResult(state: LiveRoomState, result: PollResult): LiveRoomState {
  if (result.ok) {
    return { phase: "connected", room: result.room, fetchedAt: result.at };
  }
  if (state.room !== null) {
    return { ...state, phase: "recovering" };
  }
  return { ...state, phase: "unavailable" };
}

/**
 * Single-flight execution for the poll loop. While one poll is
 * running, later ticks are skipped rather than raced: responses can
 * never complete out of order, and a request slower than the poll
 * interval still lands instead of being discarded by a newer one.
 */
export function createSingleFlight(): (task: () => Promise<void>) => Promise<boolean> {
  let running = false;
  return async function run(task) {
    if (running) return false;
    running = true;
    try {
      await task();
    } finally {
      running = false;
    }
    return true;
  };
}

/**
 * One poll: fetch the room payload under a timeout, fold the outcome
 * into the state machine. A request that hangs past timeoutMs is
 * aborted and counts as a failed poll, so single-flight can never
 * starve behind a dead connection.
 */
export async function pollRoomOnce(
  fetchGames: (signal: AbortSignal) => Promise<RoomGamesPayload>,
  state: LiveRoomState,
  options: { timeoutMs: number; now?: () => number },
): Promise<LiveRoomState> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), options.timeoutMs);
  try {
    const room = await fetchGames(controller.signal);
    return applyPollResult(state, { ok: true, room, at: (options.now ?? Date.now)() });
  } catch {
    return applyPollResult(state, { ok: false });
  } finally {
    clearTimeout(timer);
  }
}
