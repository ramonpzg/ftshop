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

  test("every technical page seeds explainer frames clear of the workspace grid", () => {
    for (const page of PAGES.slice(1)) {
      const frames = getPageSeedShapes(page.slug).filter((shape) => shape.kind === "frame");
      expect(frames.length).toBeGreaterThanOrEqual(2);
      for (const frame of frames) {
        expect(frame.name).toContain("Explainer");
        // Workspaces are generated from y=1500 down starting at x=0;
        // explainers must never overlap that band.
        expect(frame.y + frame.h).toBeLessThan(1500);
        expect(frame.x).toBeGreaterThanOrEqual(1400);
      }
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

  test("video page maps chess to a detailed real-world scene", () => {
    const text = getPageSeedShapes("real-world-video")
      .map((shape) => (shape.kind === "frame" ? `${shape.name} ${shape.prompt}` : shape.text))
      .join(" ");

    expect(text).toContain("Luna");
    expect(text).toContain("real-world");
    expect(text).toContain("camera");
    expect(text.toLowerCase()).not.toContain("chess moments");
  });
});
