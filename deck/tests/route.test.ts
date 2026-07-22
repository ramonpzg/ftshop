/** The default route is encoded, not aspirational: slides.md imports
 * each section with a range that excludes exactly the slides whose
 * speaker notes say OPTIONAL, and slides-full.md imports everything.
 * Slide indices come from the TIMING note blocks, one per slide by
 * the note contract. */

import { describe, expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import { join } from "node:path";

const DECK = join(import.meta.dir, "..");
const SECTIONS = [
  "01-origin.md",
  "02-outcomes.md",
  "03-why-adapt.md",
  "04-chess-primer.md",
  "05-technical-reference.md",
];

function noteBlocks(file: string): string[] {
  const text = readFileSync(join(DECK, "slides", file), "utf8");
  return (text.match(/<!--[\s\S]*?-->/g) ?? []).filter((block) => block.includes("TIMING:"));
}

/** The subset of Slidev's range syntax the entries use: "1-3,5-8". */
function expandRange(rangeStr: string): number[] {
  const out: number[] = [];
  for (const part of rangeStr.split(",")) {
    if (part.includes("-")) {
      const [from, to] = part.split("-").map(Number);
      for (let i = from; i <= to; i += 1) out.push(i);
    } else {
      out.push(Number(part));
    }
  }
  return out;
}

function importsOf(entry: string): Map<string, string | null> {
  const text = readFileSync(join(DECK, entry), "utf8");
  const map = new Map<string, string | null>();
  for (const match of text.matchAll(/src: \.\/slides\/([\w-]+\.md)(?:#([\d,-]+))?/g)) {
    map.set(match[1], match[2] ?? null);
  }
  return map;
}

describe("default route encoding", () => {
  const defaults = importsOf("slides.md");
  const full = importsOf("slides-full.md");

  for (const file of SECTIONS) {
    test(`${file}: slides.md imports everything except the OPTIONAL slides`, () => {
      const notes = noteBlocks(file);
      expect(notes.length).toBeGreaterThan(0);
      const all = notes.map((_, index) => index + 1);
      const expected = all.filter((index) => !notes[index - 1].includes("OPTIONAL"));
      const range = defaults.get(file);
      expect(range !== undefined).toBe(true);
      const imported = range === null || range === undefined ? all : expandRange(range);
      expect(imported).toEqual(expected);
    });

    test(`${file}: slides-full.md imports every slide, no range`, () => {
      expect(full.get(file)).toBeNull();
    });
  }

  test("the optional slides are the nine named in the plan", () => {
    // Oscar, mappings two and three, the model tree, the four A/B
    // guessing slides, and their reveal.
    const optionalCount = SECTIONS.flatMap((file) => noteBlocks(file)).filter((block) =>
      block.includes("OPTIONAL"),
    ).length;
    expect(optionalCount).toBe(9);
  });
});
