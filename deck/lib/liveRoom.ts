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
