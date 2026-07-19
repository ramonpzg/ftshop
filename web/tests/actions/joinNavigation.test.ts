import { afterEach, describe, expect, mock, test } from "bun:test";
import { resolveJoinNavigation } from "../../src/actions/joinNavigation";

function presenterFetch(responses: Array<{ status: number; mode?: string }>) {
  let index = 0;
  return mock(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (!url.endsWith("/presenter")) return new Response("not found", { status: 404 });
    const step = responses[Math.min(index, responses.length - 1)];
    index += 1;
    if (step.status !== 200) return new Response("boom", { status: step.status });
    return new Response(
      JSON.stringify({
        mode: step.mode ?? "idle",
        locked: false,
        active_page_slug: null,
        focused_user_id: null,
        updated_at: "now",
        revision: 1,
        target_frame_id: null,
        target_bounds: null,
      }),
    );
  }) as unknown as typeof fetch;
}

afterEach(() => {
  mock.restore();
});

describe("resolveJoinNavigation", () => {
  test("a 500 then a successful idle read still sends the attendee to their workspace", async () => {
    globalThis.fetch = presenterFetch([{ status: 500 }, { status: 200, mode: "idle" }]);
    const navigation = await resolveJoinNavigation({ delayMs: 5 });
    expect(navigation).toBe("workspace");
  });

  test("a confirmed presenter mode stays put", async () => {
    globalThis.fetch = presenterFetch([{ status: 200, mode: "presenter" }]);
    expect(await resolveJoinNavigation({ delayMs: 5 })).toBe("stay");
  });

  test("a confirmed workspaces mode navigates", async () => {
    globalThis.fetch = presenterFetch([{ status: 500 }, { status: 200, mode: "workspaces" }]);
    expect(await resolveJoinNavigation({ delayMs: 5 })).toBe("workspace");
  });

  test("an exhausted retry budget stays put and leaves navigation to the presenter poll", async () => {
    globalThis.fetch = presenterFetch([{ status: 500 }]);
    expect(await resolveJoinNavigation({ attempts: 3, delayMs: 5 })).toBe("stay");
  });

  test("cancellation stops the retry loop", async () => {
    globalThis.fetch = presenterFetch([{ status: 500 }]);
    let calls = 0;
    const navigation = await resolveJoinNavigation({
      attempts: 10,
      delayMs: 5,
      isCancelled: () => {
        calls += 1;
        return calls > 2;
      },
    });
    expect(navigation).toBe("stay");
    expect(calls).toBeLessThanOrEqual(4);
  });
});
