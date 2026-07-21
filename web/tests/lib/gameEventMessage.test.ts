import { describe, expect, test } from "bun:test";
import {
  GAME_EVENT_MESSAGES,
  type GameEventKind,
  gameEventMessage,
} from "../../src/lib/gameEventMessage";

describe("game event messages", () => {
  test("every event has one factual label", () => {
    expect(GAME_EVENT_MESSAGES).toEqual({
      check: "Check.",
      checkmate: "Checkmate. The model won.",
      win: "Checkmate. You won.",
      loss: "Loss recorded.",
    });
  });

  test("returns the label for the requested event", () => {
    for (const kind of Object.keys(GAME_EVENT_MESSAGES) as GameEventKind[]) {
      expect(gameEventMessage(kind)).toBe(GAME_EVENT_MESSAGES[kind]);
    }
  });
});
