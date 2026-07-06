import { describe, expect, test } from "bun:test";
import { orderSlides, type SlideFrame, stepSlideIndex } from "../../src/calculations/slides";

function frame(name: string, x = 0, y = 0): SlideFrame {
  return { id: `shape:${name}-${x}-${y}`, name, x, y };
}

describe("orderSlides", () => {
  test("orders by name with numeric awareness", () => {
    const frames = [frame("Slide 10"), frame("Slide 2"), frame("Slide 1")];
    expect(orderSlides(frames).map((f) => f.name)).toEqual(["Slide 1", "Slide 2", "Slide 10"]);
  });

  test("breaks name ties by x then y", () => {
    const frames = [frame("Slide", 200, 0), frame("Slide", 0, 300), frame("Slide", 0, 0)];
    expect(orderSlides(frames).map((f) => [f.x, f.y])).toEqual([
      [0, 0],
      [0, 300],
      [200, 0],
    ]);
  });

  test("does not mutate the input", () => {
    const frames = [frame("b"), frame("a")];
    orderSlides(frames);
    expect(frames.map((f) => f.name)).toEqual(["b", "a"]);
  });
});

describe("stepSlideIndex", () => {
  test("steps forward and backward", () => {
    expect(stepSlideIndex(0, 5, 1)).toBe(1);
    expect(stepSlideIndex(3, 5, -1)).toBe(2);
  });

  test("clamps at both ends", () => {
    expect(stepSlideIndex(4, 5, 1)).toBe(4);
    expect(stepSlideIndex(0, 5, -1)).toBe(0);
  });

  test("entering the deck from no selection lands on first or last", () => {
    expect(stepSlideIndex(-1, 5, 1)).toBe(0);
    expect(stepSlideIndex(-1, 5, -1)).toBe(4);
  });

  test("empty deck stays at -1", () => {
    expect(stepSlideIndex(-1, 0, 1)).toBe(-1);
    expect(stepSlideIndex(2, 0, -1)).toBe(-1);
  });
});
