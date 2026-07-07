import { describe, expect, test } from "bun:test";
import { BANTER, type BanterKind, pickBanter } from "../../src/lib/gameBanter";

describe("banter pools", () => {
  test("every kind has lines and none are empty", () => {
    for (const kind of Object.keys(BANTER) as BanterKind[]) {
      expect(BANTER[kind].length).toBeGreaterThan(2);
      for (const line of BANTER[kind]) {
        expect(line.length).toBeGreaterThan(0);
      }
    }
  });

  test("rotation walks the pool and wraps around", () => {
    const pool = BANTER.loss;
    expect(pickBanter("loss", 0)).toBe(pool[0]);
    expect(pickBanter("loss", 1)).toBe(pool[1]);
    expect(pickBanter("loss", pool.length)).toBe(pool[0]);
  });

  test("consecutive indexes never repeat a line", () => {
    for (let i = 0; i < 10; i++) {
      expect(pickBanter("check", i)).not.toBe(pickBanter("check", i + 1));
    }
  });
});
