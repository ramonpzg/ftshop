import { describe, expect, test } from "bun:test";
import { PAGES, PAGE_TABS } from "../../src/lib/pages";

describe("workshop page navigation", () => {
  test("keeps the presentation fallback out of the visible tabs", () => {
    expect(PAGES.map((page) => page.slug)).toContain("presentation");
    expect(PAGE_TABS.map((page) => page.slug)).toEqual([
      "chess-machine",
      "painting-pieces",
      "board-sound",
      "real-world-video",
    ]);
  });
});
