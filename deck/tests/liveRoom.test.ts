import { describe, expect, test } from "bun:test";
import {
  applyPollResult,
  INITIAL_LIVE_ROOM_STATE,
  type LiveRoomState,
  type RoomGamesPayload,
} from "../lib/liveRoom";

const ROOM: RoomGamesPayload = {
  games: [{ id: "g1", user_name: "Ada", result: null }],
  playing: 1,
  finished: 0,
  total_dataset_rows: 12,
};

describe("LiveRoom state machine", () => {
  test("starts connecting, with nothing to show", () => {
    expect(INITIAL_LIVE_ROOM_STATE.phase).toBe("connecting");
    expect(INITIAL_LIVE_ROOM_STATE.room).toBeNull();
  });

  test("a successful poll connects and carries the payload", () => {
    const state = applyPollResult(INITIAL_LIVE_ROOM_STATE, { ok: true, room: ROOM, at: 1000 });
    expect(state.phase).toBe("connected");
    expect(state.room).toEqual(ROOM);
    expect(state.fetchedAt).toBe(1000);
  });

  test("failing before any data means unavailable", () => {
    const state = applyPollResult(INITIAL_LIVE_ROOM_STATE, { ok: false });
    expect(state.phase).toBe("unavailable");
    expect(state.room).toBeNull();
  });

  test("failing after data means recovering, and the stale data stays visible", () => {
    const connected = applyPollResult(INITIAL_LIVE_ROOM_STATE, { ok: true, room: ROOM, at: 1000 });
    const state = applyPollResult(connected, { ok: false });
    expect(state.phase).toBe("recovering");
    expect(state.room).toEqual(ROOM);
    expect(state.fetchedAt).toBe(1000);
  });

  test("recovering returns to connected on the next good poll", () => {
    const recovering: LiveRoomState = { phase: "recovering", room: ROOM, fetchedAt: 1000 };
    const state = applyPollResult(recovering, { ok: true, room: ROOM, at: 4000 });
    expect(state.phase).toBe("connected");
    expect(state.fetchedAt).toBe(4000);
  });

  test("staying down while holding data keeps recovering, never unavailable", () => {
    let state = applyPollResult(INITIAL_LIVE_ROOM_STATE, { ok: true, room: ROOM, at: 1000 });
    for (let i = 0; i < 5; i++) state = applyPollResult(state, { ok: false });
    expect(state.phase).toBe("recovering");
    expect(state.room).toEqual(ROOM);
  });
});

describe("createLatestGate", () => {
  test("only the newest token may apply", async () => {
    const { createLatestGate } = await import("../lib/liveRoom");
    const gate = createLatestGate();
    const slow = gate.begin();
    const fast = gate.begin();
    expect(gate.isCurrent(fast)).toBe(true);
    expect(gate.isCurrent(slow)).toBe(false);
  });

  test("a stale success cannot overwrite a newer failure's recovery state", async () => {
    const { createLatestGate } = await import("../lib/liveRoom");
    const gate = createLatestGate();
    let state = applyPollResult(INITIAL_LIVE_ROOM_STATE, { ok: true, room: ROOM, at: 1000 });

    const stale = gate.begin(); // poll starts, will resolve late
    const fresh = gate.begin(); // next poll starts and fails first
    if (gate.isCurrent(fresh)) state = applyPollResult(state, { ok: false });
    expect(state.phase).toBe("recovering");

    // The stale response finally lands; the gate discards it.
    if (gate.isCurrent(stale)) state = applyPollResult(state, { ok: true, room: ROOM, at: 900 });
    expect(state.phase).toBe("recovering");
    expect(state.fetchedAt).toBe(1000);
  });
});
