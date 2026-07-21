/** Visible workshop copy, checked across the deck, web app, and the
 * two presenter run-of-show documents. */

import { describe, expect, test } from "bun:test";
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { checkCopy } from "../lib/copyRules";

const DECK_ROOT = join(import.meta.dir, "..");
const REPO_ROOT = join(DECK_ROOT, "..");

function filesUnder(root: string, extensions: Set<string>): string[] {
  return readdirSync(root, { withFileTypes: true }).flatMap((entry) => {
    const path = join(root, entry.name);
    if (entry.isDirectory()) return filesUnder(path, extensions);
    const extension = entry.name.slice(entry.name.lastIndexOf("."));
    return extensions.has(extension) ? [path] : [];
  });
}

function deckFiles(): string[] {
  const slides = readdirSync(join(DECK_ROOT, "slides"))
    .filter((name) => name.endsWith(".md"))
    .map((name) => join(DECK_ROOT, "slides", name));
  const components = readdirSync(join(DECK_ROOT, "components"))
    .filter((name) => name.endsWith(".vue"))
    .map((name) => join(DECK_ROOT, "components", name));
  const lib = readdirSync(join(DECK_ROOT, "lib"))
    // copyRules.ts defines the banned list and cannot pass its own scan.
    .filter((name) => name.endsWith(".ts") && name !== "copyRules.ts")
    .map((name) => join(DECK_ROOT, "lib", name));
  return [
    join(DECK_ROOT, "slides.md"),
    join(DECK_ROOT, "slides-full.md"),
    join(DECK_ROOT, "style.css"),
    ...slides,
    ...components,
    ...lib,
  ];
}

describe("deck copy", () => {
  for (const file of deckFiles()) {
    test(`no banned punctuation or stock phrases in ${file.slice(DECK_ROOT.length + 1)}`, () => {
      const findings = checkCopy(readFileSync(file, "utf8"));
      expect(findings).toEqual([]);
    });
  }
});

describe("repository copy", () => {
  const files = [
    join(REPO_ROOT, "docs", "session-plan.md"),
    join(REPO_ROOT, "docs", "demo-plan.md"),
    ...filesUnder(join(REPO_ROOT, "web", "src"), new Set([".ts", ".tsx"])),
  ];

  for (const file of files) {
    test(`no banned punctuation or stock phrases in ${file.slice(REPO_ROOT.length + 1)}`, () => {
      const findings = checkCopy(readFileSync(file, "utf8"));
      expect(findings).toEqual([]);
    });
  }
});

const NOTE_TAGS = ["TIMING:", "SAY:", "CLICK:", "SOURCE:", "CUT:", "FALLBACK:"];

describe("speaker-note contract", () => {
  // Section files only: the two entry files hold headmatter and
  // imports, not content slides.
  const slideFiles = deckFiles().filter((file) => file.includes("/slides/"));
  for (const file of slideFiles) {
    test(`every note block carries all six tags in ${file.slice(DECK_ROOT.length + 1)}`, () => {
      const text = readFileSync(file, "utf8");
      const blocks = text.match(/<!--[\s\S]*?-->/g) ?? [];
      const noteBlocks = blocks.filter((block) => block.includes("TIMING:"));
      expect(noteBlocks.length).toBeGreaterThan(0);
      for (const block of noteBlocks) {
        for (const tag of NOTE_TAGS) {
          expect(block).toContain(tag);
        }
      }
    });
  }
});

describe("placeholder inventory", () => {
  test("every asset referenced by the slides is in the deck-plan inventory", () => {
    const inventory = readFileSync(join(DECK_ROOT, "..", "docs", "deck-plan.md"), "utf8");
    const slideFiles = deckFiles().filter((file) => file.endsWith(".md"));
    const referenced = new Set<string>();
    for (const file of slideFiles) {
      const text = readFileSync(file, "utf8");
      for (const match of text.matchAll(/file="([^"]+)"/g)) {
        referenced.add(match[1]);
      }
    }
    expect(referenced.size).toBeGreaterThan(0);
    const missing = [...referenced].filter((asset) => !inventory.includes(asset));
    expect(missing).toEqual([]);
  });
});
