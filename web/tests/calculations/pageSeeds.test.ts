import { describe, expect, test } from "bun:test";
import { getPageSeedShapes } from "../../src/calculations/pageSeeds";
import { PAGES } from "../../src/lib/pages";

describe("getPageSeedShapes", () => {
  test("every page has seed content", () => {
    for (const page of PAGES) {
      const shapes = getPageSeedShapes(page.slug);
      expect(shapes.length).toBeGreaterThan(0);
    }
  });

  test("every page opens with a heading", () => {
    for (const page of PAGES) {
      const [first] = getPageSeedShapes(page.slug);
      expect(first.kind).toBe("heading");
    }
  });

  test("no seed text is empty", () => {
    for (const page of PAGES) {
      for (const shape of getPageSeedShapes(page.slug)) {
        expect(shape.text.trim().length).toBeGreaterThan(0);
      }
    }
  });

  test("throws for an unknown page slug", () => {
    expect(() => getPageSeedShapes("not-a-page")).toThrow();
  });

  test("chess-machine page mentions the core technical topics", () => {
    const text = getPageSeedShapes("chess-machine")
      .map((s) => s.text)
      .join(" ");
    for (const topic of ["Prompt template", "LoRA", "RL environment", "Stockfish", "Evals"]) {
      expect(text).toContain(topic);
    }
  });
});
