import { describe, expect, test } from "bun:test";
import { computeWorkspacePosition, WORKSPACE_DIMENSIONS } from "../../src/calculations/layout";

describe("computeWorkspacePosition", () => {
  test("places the first workspace at the origin", () => {
    expect(computeWorkspacePosition(0)).toEqual({ x: 0, y: 0 });
  });

  test("advances columns before wrapping to a new row", () => {
    const first = computeWorkspacePosition(0);
    const second = computeWorkspacePosition(1);
    expect(second.x).toBeGreaterThan(first.x);
    expect(second.y).toBe(first.y);
  });

  test("wraps to a new row after three columns", () => {
    const wrapped = computeWorkspacePosition(3);
    expect(wrapped.x).toBe(0);
    expect(wrapped.y).toBeGreaterThan(0);
  });

  test("never overlaps workspace bounds between adjacent columns", () => {
    const a = computeWorkspacePosition(0);
    const b = computeWorkspacePosition(1);
    expect(b.x - a.x).toBeGreaterThanOrEqual(WORKSPACE_DIMENSIONS.width);
  });

  test("rejects negative or non-integer indices", () => {
    expect(() => computeWorkspacePosition(-1)).toThrow();
    expect(() => computeWorkspacePosition(1.5)).toThrow();
  });
});
