/** prefers-reduced-motion was an explicit phase requirement: every
 * final state must read as a static frame. The mechanism is one global
 * CSS block; this test pins its existence and its coverage so a style
 * refactor cannot silently drop it. A live-browser check with
 * emulateMedia is part of the screenshot pass and recorded in the
 * handover. */

import { describe, expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import { join } from "node:path";

const css = readFileSync(join(import.meta.dir, "..", "style.css"), "utf8");

function reducedMotionBlock(): string {
  const start = css.indexOf("@media (prefers-reduced-motion: reduce)");
  expect(start).toBeGreaterThan(-1);
  // The block ends at the first closing brace pair after its rules.
  const slice = css.slice(start);
  let depth = 0;
  for (let i = 0; i < slice.length; i += 1) {
    if (slice[i] === "{") depth += 1;
    if (slice[i] === "}") {
      depth -= 1;
      if (depth === 0) return slice.slice(0, i + 1);
    }
  }
  throw new Error("unclosed reduced-motion block");
}

describe("prefers-reduced-motion", () => {
  const block = reducedMotionBlock();

  test("collapses transition and animation durations, with priority", () => {
    expect(block).toContain("transition-duration: 1ms !important");
    expect(block).toContain("animation-duration: 1ms !important");
  });

  test("zeroes delays so nothing waits before settling", () => {
    expect(block).toContain("transition-delay: 0ms !important");
    expect(block).toContain("animation-delay: 0ms !important");
  });

  test("applies universally, including pseudo elements", () => {
    expect(block).toContain("*,");
    expect(block).toContain("::before");
    expect(block).toContain("::after");
  });
});
