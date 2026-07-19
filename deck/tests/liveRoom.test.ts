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

describe("single-flight polling", () => {
  const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

  test("a poll slower than the interval still lands instead of being discarded", async () => {
    const { createSingleFlight, pollRoomOnce } = await import("../lib/liveRoom");
    const runPoll = createSingleFlight();
    let state = INITIAL_LIVE_ROOM_STATE;
    // A four-second-style request, scaled down: resolves after 40ms
    // while the "interval" ticks every 10ms.
    const slowFetch = async () => {
      await wait(40);
      return ROOM;
    };
    const first = runPoll(async () => {
      state = await pollRoomOnce(slowFetch, state, { timeoutMs: 1000, now: () => 1000 });
    });
    // Interval ticks arriving mid-flight are skipped, not raced.
    for (let i = 0; i < 3; i++) {
      await wait(10);
      expect(
        await runPoll(async () => {
          state = await pollRoomOnce(slowFetch, state, { timeoutMs: 1000 });
        }),
      ).toBe(false);
    }
    await first;
    // The slow response was applied: no starvation in connecting.
    expect(state.phase).toBe("connected");
    expect(state.room).toEqual(ROOM);
  });

  test("a hung request is aborted at the timeout and counts as a failed poll", async () => {
    const { pollRoomOnce } = await import("../lib/liveRoom");
    const hangingFetch = (signal: AbortSignal) =>
      new Promise<never>((_, reject) => {
        signal.addEventListener("abort", () => reject(new Error("aborted")));
      });
    const state = await pollRoomOnce(hangingFetch, INITIAL_LIVE_ROOM_STATE, { timeoutMs: 20 });
    expect(state.phase).toBe("unavailable");
  });

  test("after the flight finishes, the next tick polls again", async () => {
    const { createSingleFlight } = await import("../lib/liveRoom");
    const runPoll = createSingleFlight();
    let runs = 0;
    await runPoll(async () => {
      runs += 1;
    });
    await runPoll(async () => {
      runs += 1;
    });
    expect(runs).toBe(2);
  });

  test("a failing task releases the flight for the next poll", async () => {
    const { createSingleFlight } = await import("../lib/liveRoom");
    const runPoll = createSingleFlight();
    await runPoll(async () => {
      throw new Error("boom");
    }).catch(() => {});
    let ran = false;
    await runPoll(async () => {
      ran = true;
    });
    expect(ran).toBe(true);
  });
});
