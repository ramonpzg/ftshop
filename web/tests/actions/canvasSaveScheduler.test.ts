import { describe, expect, test } from "bun:test";
import { createSaveScheduler, type SaveStatus } from "../../src/actions/canvasSaveScheduler";
import type { CanvasSnapshot } from "../../src/data/api";

function wait(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

interface Harness {
  saves: CanvasSnapshot[];
  statuses: SaveStatus[];
  failNext: { count: number };
}

function makeHarness(overrides: { debounceMs?: number; retryMs?: number } = {}) {
  const harness: Harness = { saves: [], statuses: [], failNext: { count: 0 } };
  let version = 0;
  const scheduler = createSaveScheduler({
    getSnapshot: () => ({ version: ++version }),
    save: async (snapshot) => {
      if (harness.failNext.count > 0) {
        harness.failNext.count -= 1;
        throw new Error("backend down");
      }
      harness.saves.push(snapshot);
    },
    debounceMs: overrides.debounceMs ?? 5,
    retryMs: overrides.retryMs ?? 10,
    onStatusChange: (status) => harness.statuses.push(status),
  });
  return { harness, scheduler };
}

describe("createSaveScheduler", () => {
  test("debounces a burst of changes into one save", async () => {
    const { harness, scheduler } = makeHarness();
    scheduler.markDirty();
    scheduler.markDirty();
    scheduler.markDirty();
    await wait(30);
    expect(harness.saves.length).toBe(1);
    expect(scheduler.status()).toBe("saved");
    scheduler.dispose();
  });

  test("changes during an in-flight save trigger a follow-up save", async () => {
    const harness: Harness = { saves: [], statuses: [], failNext: { count: 0 } };
    let resolveFirst: () => void = () => {};
    let calls = 0;
    const scheduler = createSaveScheduler({
      getSnapshot: () => ({ call: calls }),
      save: (snapshot) => {
        calls += 1;
        harness.saves.push(snapshot);
        if (calls === 1) {
          return new Promise<void>((resolve) => {
            resolveFirst = resolve;
          });
        }
        return Promise.resolve();
      },
      debounceMs: 1,
    });

    scheduler.markDirty();
    await wait(10);
    expect(calls).toBe(1);
    scheduler.markDirty();
    resolveFirst();
    await wait(20);
    expect(calls).toBe(2);
    scheduler.dispose();
  });

  test("failed save keeps data dirty and retries", async () => {
    const { harness, scheduler } = makeHarness({ retryMs: 5 });
    harness.failNext.count = 1;
    scheduler.markDirty();
    await wait(40);
    expect(harness.saves.length).toBe(1);
    expect(harness.statuses).toContain("error");
    expect(scheduler.status()).toBe("saved");
    scheduler.dispose();
  });

  test("flush saves immediately without waiting for the debounce", async () => {
    const { harness, scheduler } = makeHarness({ debounceMs: 10_000 });
    scheduler.markDirty();
    const clean = await scheduler.flush();
    expect(clean).toBe(true);
    expect(harness.saves.length).toBe(1);
    scheduler.dispose();
  });

  test("flush reports false when the save fails and dirty state remains", async () => {
    const { harness, scheduler } = makeHarness({ debounceMs: 10_000 });
    harness.failNext.count = 10;
    scheduler.markDirty();
    const clean = await scheduler.flush();
    expect(clean).toBe(false);
    expect(scheduler.status()).toBe("error");
    // A later flush after the backend recovers drains the dirty state.
    harness.failNext.count = 0;
    expect(await scheduler.flush()).toBe(true);
    expect(harness.saves.length).toBe(1);
    scheduler.dispose();
  });

  test("flush does nothing when clean", async () => {
    const { harness, scheduler } = makeHarness();
    await scheduler.flush();
    expect(harness.saves.length).toBe(0);
    expect(scheduler.status()).toBe("idle");
    scheduler.dispose();
  });

  test("dispose cancels pending saves", async () => {
    const { harness, scheduler } = makeHarness({ debounceMs: 5 });
    scheduler.markDirty();
    scheduler.dispose();
    await wait(20);
    expect(harness.saves.length).toBe(0);
  });
});
