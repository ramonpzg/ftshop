import { describe, expect, test } from "bun:test";
import { getSnippetById, SNIPPETS } from "../../src/lib/snippets";

describe("SNIPPETS", () => {
  test("has exactly the eight required snippets", () => {
    expect(SNIPPETS.map((s) => s.id).sort()).toEqual(
      [
        "axolotl_config",
        "chat_template",
        "dataset_row_builder",
        "fine_tune",
        "jax_train",
        "legal_move_validation",
        "prompt_template",
        "reward_function",
      ].sort(),
    );
  });

  test("training snippets load the exported dataset file", () => {
    for (const id of ["fine_tune", "axolotl_config"]) {
      expect(getSnippetById(id).code).toContain("data/processed/text/chess_sft.jsonl");
    }
  });

  test("the axolotl snippet is yaml, the rest are python", () => {
    expect(getSnippetById("axolotl_config").language).toBe("yaml");
    expect(getSnippetById("fine_tune").language).toBe("python");
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
