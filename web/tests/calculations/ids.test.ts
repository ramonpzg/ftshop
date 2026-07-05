import { describe, expect, test } from "bun:test";
import { generateLocalId, workspaceShapeId } from "../../src/calculations/ids";

describe("generateLocalId", () => {
  test("prefixes the id", () => {
    expect(generateLocalId("user")).toStartWith("user_");
  });

  test("generates unique ids", () => {
    const ids = new Set(Array.from({ length: 100 }, () => generateLocalId("user")));
    expect(ids.size).toBe(100);
  });
});

describe("workspaceShapeId", () => {
  test("is deterministic for the same user and page", () => {
    expect(workspaceShapeId("user_1", "chess-machine")).toBe(
      workspaceShapeId("user_1", "chess-machine"),
    );
  });

  test("differs across pages", () => {
    expect(workspaceShapeId("user_1", "chess-machine")).not.toBe(
      workspaceShapeId("user_1", "painting-pieces"),
    );
  });
});
