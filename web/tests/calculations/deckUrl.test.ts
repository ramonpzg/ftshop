import { describe, expect, test } from "bun:test";
import { resolveDeckUrl } from "../../src/calculations/deckUrl";

describe("resolveDeckUrl", () => {
  test("keeps localhost when the app itself is viewed on localhost", () => {
    expect(resolveDeckUrl("http://localhost:3030", "localhost")).toBe("http://localhost:3030");
    expect(resolveDeckUrl("http://localhost:3030", "127.0.0.1")).toBe("http://localhost:3030");
  });

  test("rewrites localhost to the presenter host for a LAN attendee", () => {
    expect(resolveDeckUrl("http://localhost:3030", "192.168.4.17")).toBe(
      "http://192.168.4.17:3030/",
    );
    expect(resolveDeckUrl("http://127.0.0.1:3030/slides", "192.168.4.17")).toBe(
      "http://192.168.4.17:3030/slides",
    );
  });

  test("respects an explicit non-local deck URL", () => {
    expect(resolveDeckUrl("http://deck-machine.local:3030", "192.168.4.17")).toBe(
      "http://deck-machine.local:3030",
    );
  });

  test("leaves an unparseable value alone", () => {
    expect(resolveDeckUrl("not a url", "192.168.4.17")).toBe("not a url");
  });
});
