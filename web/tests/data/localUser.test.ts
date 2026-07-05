import { beforeEach, describe, expect, test } from "bun:test";
import { clearLocalUser, loadLocalUser, saveLocalUser } from "../../src/data/localUser";

beforeEach(() => {
  localStorage.clear();
});

describe("localUser", () => {
  test("returns null when nothing is saved", () => {
    expect(loadLocalUser()).toBeNull();
  });

  test("round-trips a saved user", () => {
    saveLocalUser({ id: "user_1", name: "Ada" });
    expect(loadLocalUser()).toEqual({ id: "user_1", name: "Ada" });
  });

  test("clear removes the saved user", () => {
    saveLocalUser({ id: "user_1", name: "Ada" });
    clearLocalUser();
    expect(loadLocalUser()).toBeNull();
  });

  test("returns null for corrupted storage", () => {
    localStorage.setItem("euro-chess-studio:current-user", "{not json");
    expect(loadLocalUser()).toBeNull();
  });
});
