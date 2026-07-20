import { describe, expect, test } from "bun:test";
import { ApiError, apiErrorCode, apiErrorDetail } from "../../src/data/api";

function errorWithDetail(detail: unknown): ApiError {
  return new ApiError(409, JSON.stringify({ detail }));
}

describe("apiErrorDetail", () => {
  test("returns a plain string detail unchanged", () => {
    expect(apiErrorDetail(errorWithDetail("scenario already reviewed"))).toBe(
      "scenario already reviewed",
    );
  });

  test("extracts message from a structured {code, message} detail", () => {
    const error = errorWithDetail({ code: "not_your_turn", message: "it is the model's turn" });
    expect(apiErrorDetail(error)).toBe("it is the model's turn");
  });

  test("falls back to the raw body when detail is missing", () => {
    const error = new ApiError(500, "not json at all");
    expect(apiErrorDetail(error)).toBe("not json at all");
  });

  test("returns null for a non-ApiError", () => {
    expect(apiErrorDetail(new Error("boom"))).toBeNull();
  });
});

describe("apiErrorCode", () => {
  test("extracts the stable code from a structured detail", () => {
    const error = errorWithDetail({ code: "clock_expired", message: "time ran out" });
    expect(apiErrorCode(error)).toBe("clock_expired");
  });

  test("reproduces the reported gap being closed: a copy edit to the message alone does not change the code", () => {
    // The whole point of a stable code is that prose can change freely
    // without silently flipping which branch a client takes. Two
    // different messages, same code, must resolve to the same code.
    const original = errorWithDetail({
      code: "not_your_turn",
      message: "it is the participant's turn; the model cannot move for them",
    });
    const reworded = errorWithDetail({
      code: "not_your_turn",
      message: "Sorry, that's not your move to make right now.",
    });
    expect(apiErrorCode(original)).toBe("not_your_turn");
    expect(apiErrorCode(reworded)).toBe("not_your_turn");
  });

  test("returns null for a plain string detail", () => {
    expect(apiErrorCode(errorWithDetail("scenario already reviewed"))).toBeNull();
  });

  test("returns null when there is no error body at all", () => {
    expect(apiErrorCode(new Error("network down"))).toBeNull();
  });
});
