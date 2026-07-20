import { describe, expect, test } from "bun:test";
import { checkCopy } from "../lib/copyRules";

describe("checkCopy", () => {
  test("clean copy passes", () => {
    expect(checkCopy("Pairs in. Adapter out. Eval always.")).toEqual([]);
  });

  test("flags an em dash with its line number", () => {
    const findings = checkCopy("fine\na claim — with a dash\nfine");
    expect(findings).toHaveLength(1);
    expect(findings[0].line).toBe(2);
    expect(findings[0].rule).toBe("em dash");
  });

  test("flags emoji but not chess glyphs", () => {
    expect(checkCopy("great work \u{1F680}")).toHaveLength(1);
    expect(checkCopy("sparkle ✨")).toHaveLength(1);
    expect(checkCopy("the knight ♞ takes ♙")).toEqual([]);
  });

  test("flags banned stock phrases case-insensitively", () => {
    expect(checkCopy("Rooks Before Feelings")).toHaveLength(1);
    expect(checkCopy("a GPU-hour is pocket money")).toHaveLength(1);
    expect(checkCopy("real bytes, not vibes")).toHaveLength(1);
  });

  test("flags cliche words only on word boundaries", () => {
    expect(checkCopy("it feels like magic")).toHaveLength(1);
    expect(checkCopy("your fine-tuning journey")).toHaveLength(1);
    expect(checkCopy("unlock the weights")).toHaveLength(1);
    // No false positive inside ordinary words.
    expect(checkCopy("the magistrate unlocked nothing")).toEqual([]);
  });

  test("the allowlist admits Slidev magic-move syntax without admitting the word", () => {
    expect(checkCopy("````md magic-move {lines: true}")).toEqual([]);
    expect(checkCopy("magic-move is magic")).toHaveLength(1);
  });
});
