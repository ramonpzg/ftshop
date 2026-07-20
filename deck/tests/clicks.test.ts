import { describe, expect, test } from "bun:test";
import { compareState, revealedRows, stepIndex, universeState } from "../lib/clicks";

describe("stepIndex", () => {
  test("starts on step zero and advances one step per click", () => {
    expect(stepIndex(0, 6)).toBe(0);
    expect(stepIndex(1, 6)).toBe(1);
    expect(stepIndex(5, 6)).toBe(5);
  });

  test("clamps past the last step and below zero", () => {
    expect(stepIndex(9, 6)).toBe(5);
    expect(stepIndex(-2, 6)).toBe(0);
  });

  test("backward navigation lands on the exact earlier frame", () => {
    // Forward to click 4, back to click 2: same state as first visit.
    const forward = stepIndex(2, 6);
    stepIndex(4, 6);
    expect(stepIndex(2, 6)).toBe(forward);
  });
});

describe("revealedRows", () => {
  test("one row per click, capped at the row count", () => {
    expect(revealedRows(0, 4)).toBe(0);
    expect(revealedRows(3, 4)).toBe(3);
    expect(revealedRows(7, 4)).toBe(4);
  });

  test("negative clicks reveal nothing", () => {
    expect(revealedRows(-1, 4)).toBe(0);
  });
});

describe("universeState", () => {
  test("first circle is visible before any click", () => {
    expect(universeState(0)).toEqual({ circlesVisible: 1, splitVisible: false });
  });

  test("four clicks show all five circles, no split yet", () => {
    expect(universeState(4)).toEqual({ circlesVisible: 5, splitVisible: false });
  });

  test("the fifth click draws the train/eval split", () => {
    expect(universeState(5)).toEqual({ circlesVisible: 5, splitVisible: true });
  });

  test("overshooting clicks stays on the final frame", () => {
    expect(universeState(9)).toEqual(universeState(5));
  });

  test("stepping backward removes the split before the circles", () => {
    expect(universeState(4).splitVisible).toBe(false);
    expect(universeState(3).circlesVisible).toBe(4);
  });
});

describe("compareState", () => {
  test("nothing is revealed before the first click", () => {
    expect(compareState(0)).toEqual({ baseVisible: false, adaptedVisible: false });
  });

  test("base lands first, adapted second", () => {
    expect(compareState(1)).toEqual({ baseVisible: true, adaptedVisible: false });
    expect(compareState(2)).toEqual({ baseVisible: true, adaptedVisible: true });
  });

  test("reverse navigation hides adapted before base", () => {
    expect(compareState(1).adaptedVisible).toBe(false);
    expect(compareState(0).baseVisible).toBe(false);
  });
});
