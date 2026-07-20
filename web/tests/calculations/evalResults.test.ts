import { describe, expect, test } from "bun:test";
import { latestEvalResultsByScope } from "../../src/calculations/evalResults";
import type { EvalResult } from "../../src/data/api";

function result(overrides: Partial<EvalResult> = {}): EvalResult {
  return {
    id: "eval_1",
    modality: "text",
    metric: "legal_move_rate",
    value: 1.0,
    workspace_id: "workspace_1",
    source: "computed",
    numerator: null,
    denominator: null,
    unit: null,
    direction: null,
    definition: null,
    version: null,
    scope_json: null,
    note: null,
    model: null,
    checkpoint: null,
    run_id: null,
    sample_ids: [],
    position_set_id: null,
    positions: [],
    created_at: "2026-01-01T00:00:00+00:00",
    ...overrides,
  };
}

describe("latestEvalResultsByScope", () => {
  test("reproduces the reported bug: three growing-window runs collapse to one", () => {
    const runs = [
      result({ id: "r1", denominator: 1, created_at: "2026-01-01T00:00:00+00:00" }),
      result({ id: "r2", denominator: 2, created_at: "2026-01-01T00:01:00+00:00" }),
      result({ id: "r3", denominator: 3, created_at: "2026-01-01T00:02:00+00:00" }),
    ];
    const latest = latestEvalResultsByScope(runs);
    expect(latest).toHaveLength(1);
    expect(latest[0].id).toBe("r3");
    expect(latest[0].denominator).toBe(3);
  });

  test("keeps different models separate", () => {
    const luna = result({ id: "luna", model: "gpt-5.6-luna" });
    const gemma = result({ id: "gemma", model: "gemma-4-2b-local" });
    const latest = latestEvalResultsByScope([luna, gemma]);
    expect(latest.map((r) => r.id).sort()).toEqual(["gemma", "luna"]);
  });

  test("keeps different checkpoints of the same model separate", () => {
    const base = result({ id: "base", model: "gemma-4-2b-local", checkpoint: "base" });
    const adapter = result({ id: "adapter", model: "gemma-4-2b-local", checkpoint: "adapter" });
    const latest = latestEvalResultsByScope([base, adapter]);
    expect(latest.map((r) => r.id).sort()).toEqual(["adapter", "base"]);
  });

  test("keeps different metrics and different workspaces separate", () => {
    const legal = result({ id: "legal", metric: "legal_move_rate" });
    const valid = result({ id: "valid", metric: "valid_json_rate" });
    const otherWorkspace = result({ id: "other_ws", workspace_id: "workspace_2" });
    const latest = latestEvalResultsByScope([legal, valid, otherWorkspace]);
    expect(latest.map((r) => r.id).sort()).toEqual(["legal", "other_ws", "valid"]);
  });

  test("keeps a cached and a computed row for the same metric separate", () => {
    const cached = result({ id: "cached", source: "cached", workspace_id: null });
    const computed = result({ id: "computed", source: "computed" });
    const latest = latestEvalResultsByScope([cached, computed]);
    expect(latest.map((r) => r.id).sort()).toEqual(["cached", "computed"]);
  });

  test("an empty list stays empty", () => {
    expect(latestEvalResultsByScope([])).toEqual([]);
  });
});
