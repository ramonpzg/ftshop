import { afterEach, describe, expect, mock, test } from "bun:test";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { AdaptationPanel } from "../../src/components/adaptation/AdaptationPanel";
import type { AdaptationState } from "../../src/data/api";

afterEach(() => {
  cleanup();
  mock.restore();
});

function baseState(): AdaptationState {
  return {
    snapshots: [
      {
        id: "snapshot_ref",
        label: "reference-sft-v1",
        modality: "text",
        origin: "seeded",
        schema_version: "sft-prompt-completion-v1",
        row_count: 24,
        excluded_ineligible_count: 0,
        source_game_count: 2,
        source_workspace_count: 0,
        scenario_raw_count: 0,
        scenario_approved_count: 0,
        content_hash: "bd4a79d8f5746adb",
        note: null,
        created_at: "2026-07-20T10:00:00",
        row_preview: [{ prompt: "p", completion: "c" }],
      },
    ],
    configs: [
      {
        config_id: "text-gemma-lora-v1",
        label: "Gemma LoRA, move SFT",
        modality: "text",
        base_model: "google/gemma-4-E2B-it-qat-q4_0-unquantized",
        method: "lora",
        lora_r: 16,
        lora_alpha: 32,
        lora_dropout: 0.05,
        learning_rate: 0.0002,
        epochs: 3,
        batch_size: 8,
        seed: 7,
        output_task: "FEN plus legal moves to one UCI move as JSON (sft-v1 contract)",
        target_checkpoint: "gemma-chess-sft-v1",
        serving_alias: "gemma-4-2b-local",
        inference_repo: "google/gemma-4-E2B-it-qat-q4_0-gguf",
        config_hash: "d0de3bd21d571650",
        limitations: "LoRA adapter over the unquantized weights.",
      },
    ],
    adapters: [],
    suites: [
      {
        id: "suite_1",
        label: "held-out-openings-v1",
        modality: "text",
        origin: "seeded",
        prompt_version: "sft-v1",
        schema_version: "bench-fen-legal-v1",
        example_count: 12,
        content_hash: "08c32382dcc38ec6",
        position_set_id: "ff526a6802915a76",
        note: null,
        created_at: "2026-07-20T10:00:00",
        examples: [
          { example_id: "ex-01", fen: "fen-1", legal_moves: ["e2e4"], prompt: "prompt-1" },
        ],
      },
    ],
    runs: [],
    comparison: null,
    live_benchmark: { available: false, model: null },
  };
}

function runRow(checkpoint: string, source = "replayed") {
  return {
    id: `run_${checkpoint}`,
    suite_id: "suite_1",
    suite_content_hash: "08c32382dcc38ec6",
    prompt_version: "sft-v1",
    checkpoint,
    model: "gemma-4-2b-local",
    provider_alias: "fixture",
    source,
    example_count: 12,
    reply_count: 12,
    transport_failed_count: 0,
    position_set_id: "ff526a6802915a76",
    note: null,
    created_at: "2026-07-20T10:05:00",
    metrics: [],
  };
}

function withComparison(state: AdaptationState): AdaptationState {
  const base = runRow("base");
  const adapted = runRow("gemma-chess-sft-v1");
  return {
    ...state,
    runs: [base, adapted],
    comparison: {
      suite_id: "suite_1",
      suite_label: "held-out-openings-v1",
      base_run: base,
      adapted_run: adapted,
      comparable: true,
      reasons: [],
      metrics: [
        {
          metric: "model_legal_move_rate",
          comparable: true,
          reason: null,
          base_value: 0.5833333333,
          adapted_value: 1.0,
          delta: 0.4166666667,
          verdict: "improved",
          unit: "ratio",
          direction: "higher_is_better",
          base_numerator: 7,
          base_denominator: 12,
          adapted_numerator: 12,
          adapted_denominator: 12,
          definition: "legal replies / replies received",
          version: "1",
          position_set_id: "ff526a6802915a76",
        },
        {
          metric: "explanation_rate",
          comparable: true,
          reason: null,
          base_value: 0.75,
          adapted_value: 0,
          delta: -0.75,
          verdict: "regressed",
          unit: "ratio",
          direction: "higher_is_better",
          base_numerator: 9,
          base_denominator: 12,
          adapted_numerator: 0,
          adapted_denominator: 12,
          definition: "replies with explanation / replies received",
          version: "1",
          position_set_id: "ff526a6802915a76",
        },
        {
          metric: "valid_json_rate",
          comparable: false,
          reason: "the runs measured different position sets (a vs b)",
          base_value: 0.83,
          adapted_value: 1.0,
          delta: null,
          verdict: null,
          unit: "ratio",
          direction: "higher_is_better",
          base_numerator: 10,
          base_denominator: 12,
          adapted_numerator: 12,
          adapted_denominator: 12,
          definition: "json replies / replies received",
          version: "2",
          position_set_id: null,
        },
      ],
      examples: [
        {
          example_id: "ex-01",
          fen: "fen-1",
          prompt: "prompt-1",
          base: {
            status: "scored",
            raw_response: 'chatty {"move": "b7b5"}',
            parsed_move: "b7b5",
            is_legal: false,
            reply_source: "replayed",
          },
          adapted: {
            status: "scored",
            raw_response: '{"move": "e2e4"}',
            parsed_move: "e2e4",
            is_legal: true,
            reply_source: "replayed",
          },
        },
      ],
    },
  };
}

function installFetch(state: () => AdaptationState) {
  const calls: Array<{ url: string; init?: RequestInit }> = [];
  globalThis.fetch = mock(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    calls.push({ url, init });
    if (url.includes("/adaptation/state")) {
      return new Response(JSON.stringify(state()), { status: 200 });
    }
    if (url.includes("/adaptation/snapshots")) {
      return new Response(JSON.stringify({ detail: "no training-eligible rows to freeze" }), {
        status: 409,
      });
    }
    if (url.includes("/jobs")) {
      return new Response(JSON.stringify({ job_config: {}, artifact: {} }), { status: 200 });
    }
    return new Response("not found", { status: 404 });
  }) as unknown as typeof fetch;
  return calls;
}

describe("AdaptationPanel", () => {
  test("renders the chain state: snapshot identity, config, suite", async () => {
    installFetch(baseState);
    render(<AdaptationPanel isEditing={true} />);
    await waitFor(() => expect(screen.getByTestId("snapshot-card")).toBeTruthy());
    expect(screen.getByTestId("snapshot-hash").textContent).toBe("bd4a79d8");
    expect(screen.getByText(/24 eligible, 0 excluded/)).toBeTruthy();
    expect(screen.getByTestId("config-card")).toBeTruthy();
    expect(
      screen.getAllByText(/google\/gemma-4-E2B-it-qat-q4_0-unquantized/).length,
    ).toBeGreaterThan(0);
    expect(screen.getByTestId("suite-card")).toBeTruthy();
    expect(screen.getByTestId("suite-psid").textContent).toBe("ff526a68");
    // No live credentials: the live button must not exist.
    expect(screen.queryByTestId("bench-base-live")).toBeNull();
    expect(screen.getByTestId("comparison-empty")).toBeTruthy();
  });

  test("shows signed deltas with verdict words and explicit refusals", async () => {
    installFetch(() => withComparison(baseState()));
    render(<AdaptationPanel isEditing={true} />);
    await waitFor(() => expect(screen.getByTestId("comparison")).toBeTruthy());
    expect(screen.getByTestId("delta-model_legal_move_rate").textContent).toBe("+0.42 improved");
    expect(screen.getByTestId("delta-explanation_rate").textContent).toBe("-0.75 regressed");
    // A mismatch is a written refusal, never a number.
    expect(screen.getByTestId("delta-valid_json_rate").textContent).toContain("Not comparable:");
    expect(screen.getByTestId("delta-valid_json_rate").textContent).toContain(
      "different position sets",
    );
    // Sample sizes are visible next to the values.
    expect(screen.getByText("7/12")).toBeTruthy();
    // The example evidence pairs base and adapted replies.
    expect(screen.getByTestId("comparison-examples")).toBeTruthy();
    expect(screen.getByText(/b7b5 \(illegal\)/)).toBeTruthy();
    expect(screen.getByText(/e2e4 \(legal\)/)).toBeTruthy();
  });

  test("a freeze refusal from the backend is shown as-is", async () => {
    installFetch(baseState);
    render(<AdaptationPanel isEditing={true} />);
    await waitFor(() => expect(screen.getByTestId("freeze-snapshot")).toBeTruthy());
    fireEvent.click(screen.getByTestId("freeze-snapshot"));
    await waitFor(() => expect(screen.getByTestId("adaptation-notice")).toBeTruthy());
    expect(screen.getByTestId("adaptation-notice").textContent).toContain(
      "no training-eligible rows",
    );
  });

  test("train and benchmark buttons run the registry jobs with honest params", async () => {
    const calls = installFetch(baseState);
    render(<AdaptationPanel isEditing={true} />);
    await waitFor(() => expect(screen.getByTestId("train-adapter")).toBeTruthy());

    fireEvent.click(screen.getByTestId("train-adapter"));
    await waitFor(() => {
      const trainCall = calls.find((call) =>
        String(call.init?.body ?? "").includes("train_adapter"),
      );
      expect(trainCall).toBeTruthy();
      const body = JSON.parse(String(trainCall?.init?.body));
      expect(body.params.dataset_snapshot_id).toBe("snapshot_ref");
      expect(body.params.config_id).toBe("text-gemma-lora-v1");
    });

    fireEvent.click(screen.getByTestId("bench-adapted"));
    await waitFor(() => {
      const benchCall = calls.find((call) =>
        String(call.init?.body ?? "").includes("gemma-chess-sft-v1"),
      );
      expect(benchCall).toBeTruthy();
      const body = JSON.parse(String(benchCall?.init?.body));
      expect(body.job_type).toBe("text.benchmark_eval");
      expect(body.params.source).toBe("replayed");
    });
  });

  test("a live run whose position set differs from the suite says so", async () => {
    const state = baseState();
    const shrunk = { ...runRow("base", "live"), reply_count: 11, transport_failed_count: 1 };
    shrunk.position_set_id = "different";
    state.runs = [shrunk];
    installFetch(() => state);
    render(<AdaptationPanel isEditing={true} />);
    await waitFor(() => expect(screen.getByTestId("benchmark-runs")).toBeTruthy());
    expect(screen.getByText(/11\/12 replies, 1 failed/)).toBeTruthy();
    expect(screen.getByText("position set differs from suite")).toBeTruthy();
  });
});
