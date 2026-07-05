import { describe, expect, test } from "bun:test";
import { getSnippetById, SNIPPETS } from "../../src/lib/snippets";

describe("SNIPPETS", () => {
  test("has exactly the four required snippets", () => {
    expect(SNIPPETS.map((s) => s.id).sort()).toEqual(
      ["dataset_row_builder", "legal_move_validation", "prompt_template", "reward_function"].sort(),
    );
  });

  test("every snippet has real, non-empty code", () => {
    for (const snippet of SNIPPETS) {
      expect(snippet.code.trim().length).toBeGreaterThan(0);
      expect(snippet.label.trim().length).toBeGreaterThan(0);
    }
  });

  test("the reward function snippet matches the backend's precedence rules", () => {
    const snippet = getSnippetById("reward_function");
    expect(snippet.code).toContain("return -1");
    expect(snippet.code).toContain("return 10");
    expect(snippet.code).toContain("return 2");
  });
});

describe("getSnippetById", () => {
  test("throws for an unknown id", () => {
    expect(() => getSnippetById("not-a-snippet")).toThrow();
  });
});
