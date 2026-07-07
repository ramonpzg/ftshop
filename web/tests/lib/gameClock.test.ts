import { describe, expect, test } from "bun:test";
import {
  DEFAULT_TIME_LIMIT_SECONDS,
  describeGameEnd,
  describeMatch,
  formatClock,
  TIME_LIMIT_CHOICES,
} from "../../src/lib/gameClock";

describe("formatClock", () => {
  test("renders minutes and zero-padded seconds", () => {
    expect(formatClock(300)).toBe("5:00");
    expect(formatClock(59.2)).toBe("1:00");
    expect(formatClock(58.4)).toBe("0:59");
    expect(formatClock(9)).toBe("0:09");
  });

  test("never goes below zero", () => {
    expect(formatClock(0)).toBe("0:00");
    expect(formatClock(-12)).toBe("0:00");
  });
});

describe("time limit choices", () => {
  test("defaults to five minutes with a thirty minute ceiling", () => {
    expect(DEFAULT_TIME_LIMIT_SECONDS).toBe(300);
    expect(TIME_LIMIT_CHOICES[0].seconds).toBe(300);
    expect(Math.max(...TIME_LIMIT_CHOICES.map((c) => c.seconds))).toBe(1800);
  });
});

describe("describeMatch", () => {
  test("states the result, move count, and clock", () => {
    expect(describeMatch({ result: "loss_timeout", legal_moves: 7, time_limit_seconds: 300 })).toBe(
      "Loss, time. 7 moves on a 5 min clock.",
    );
    expect(describeMatch({ result: "win", legal_moves: 1, time_limit_seconds: 1800 })).toBe(
      "Win, checkmate. 1 move on a 30 min clock.",
    );
  });

  test("passes unknown results through untranslated", () => {
    expect(
      describeMatch({ result: "abandoned", legal_moves: 2, time_limit_seconds: 300 }),
    ).toContain("abandoned");
  });
});

describe("describeGameEnd", () => {
  test("every ending states its consequence", () => {
    expect(describeGameEnd("loss_resign")).toContain("loss");
    expect(describeGameEnd("loss_timeout")).toContain("Time ran out");
    expect(describeGameEnd("win")).toContain("You won");
    expect(describeGameEnd("loss")).toContain("model won");
    expect(describeGameEnd("draw")).toContain("draw");
    expect(describeGameEnd("anything-else")).toBe("Game over.");
  });
});
