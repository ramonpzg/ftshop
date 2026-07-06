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
        const text = shape.kind === "frame" ? `${shape.name} ${shape.prompt}` : shape.text;
        expect(text.trim().length).toBeGreaterThan(0);
      }
    }
  });

  test("presentation page seeds a slide deck in order", () => {
    const frames = getPageSeedShapes("presentation").filter((shape) => shape.kind === "frame");
    expect(frames.length).toBeGreaterThanOrEqual(8);
    for (const [index, frame] of frames.entries()) {
      expect(frame.name).toContain(`Slide ${String(index + 1).padStart(2, "0")}`);
    }
    const uniqueX = new Set(frames.map((frame) => frame.x));
    expect(uniqueX.size).toBe(frames.length);
  });

  test("only the presentation page has slide frames", () => {
    for (const page of PAGES.slice(1)) {
      const frames = getPageSeedShapes(page.slug).filter((shape) => shape.kind === "frame");
      expect(frames.length).toBe(0);
    }
  });

  test("throws for an unknown page slug", () => {
    expect(() => getPageSeedShapes("not-a-page")).toThrow();
  });

  test("chess-machine page mentions the core technical topics", () => {
    const text = getPageSeedShapes("chess-machine")
      .map((s) => (s.kind === "frame" ? s.prompt : s.text))
      .join(" ");
    for (const topic of ["Prompt template", "LoRA", "RL environment", "Stockfish", "Evals"]) {
      expect(text).toContain(topic);
    }
  });
});
