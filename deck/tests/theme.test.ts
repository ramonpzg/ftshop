/** The chalk style is a token overlay, not a fork: every color token
 * the paper style defines must be overridden in the chalk block, or a
 * new token added to :root would silently render paper-colored on the
 * near-black ground. --ease is motion, shared by design. */

import { describe, expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import { join } from "node:path";

const css = readFileSync(join(import.meta.dir, "..", "style.css"), "utf8");

function tokensOf(selector: string): string[] {
  const start = css.indexOf(selector);
  expect(start).toBeGreaterThan(-1);
  const block = css.slice(start, css.indexOf("}", start));
  return [...block.matchAll(/(--[\w-]+):/g)].map((match) => match[1]);
}

describe("chalk style token parity", () => {
  test("chalk overrides every color token the paper style defines", () => {
    const paper = tokensOf(":root {").filter((token) => token !== "--ease");
    const chalk = tokensOf("html.style-chalk {");
    expect(chalk.sort()).toEqual([...paper].sort());
  });

  test("the chalk switch is wired to the env flag", () => {
    const setup = readFileSync(join(import.meta.dir, "..", "setup", "main.ts"), "utf8");
    expect(setup).toContain('import.meta.env.VITE_DECK_STYLE === "chalk"');
    expect(setup).toContain("style-chalk");
  });
});
