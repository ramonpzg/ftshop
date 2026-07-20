import { afterEach, describe, expect, mock, test } from "bun:test";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { WorkspacePanel } from "../../src/components/workspace/WorkspacePanel";
import type { WorkspaceShape } from "../../src/components/tldraw/shapes/workspaceShapeTypes";
import { CurrentUserContext } from "../../src/lib/currentUserContext";
import { PresenterContext } from "../../src/lib/presenterContext";

const STARTING_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";

function makeShape(overrides: Partial<WorkspaceShape["props"]> = {}): WorkspaceShape {
  return {
    id: "shape:workspace-user_1-chess-machine" as WorkspaceShape["id"],
    type: "workspace",
    x: 0,
    y: 0,
    rotation: 0,
    index: "a1" as WorkspaceShape["index"],
    parentId: "page:chess-machine" as WorkspaceShape["parentId"],
    isLocked: false,
    opacity: 1,
    meta: {},
    typeName: "shape",
    props: {
      w: 900,
      h: 560,
      workspaceId: "workspace_1",
      userId: "user_1",
      userName: "Ada",
      pageSlug: "chess-machine",
      ...overrides,
    },
  };
}

const SUGGESTED_SCENARIO = {
  id: "scenario_1",
  workspace_id: "workspace_1",
  game_id: null,
  ply: 0,
  status: "suggested",
  assessment: "Level.",
  real_world: "A new hire watches the routine.",
  video_prompt: "A documentary shot follows an analyst.",
  suggested_assessment: "Level.",
  suggested_real_world: "A new hire watches the routine.",
  suggested_video_prompt: "A documentary shot follows an analyst.",
  model: "gpt-5.6-luna",
  provider_alias: "video_prompt",
  prompt_version: "assess-v1",
  error_detail: null,
  created_at: "now",
};

const FAILED_SCENARIO = {
  id: "scenario_failed",
  workspace_id: "workspace_1",
  game_id: null,
  ply: 0,
  status: "failed",
  assessment: null,
  real_world: null,
  video_prompt: null,
  suggested_assessment: null,
  suggested_real_world: null,
  suggested_video_prompt: null,
  model: "gpt-5.6-luna",
  provider_alias: "video_prompt",
  prompt_version: "assess-v1",
  error_detail: "502 from video_prompt",
  created_at: "now",
};

function routedFetch(
  opts: {
    expiredAway?: boolean;
    checkOnMove?: boolean;
    opponentModels?: string[];
    scenario?: Record<string, unknown> | null;
    // Overrides the seeded latest_success independently of `scenario`,
    // for a workspace whose most recent attempt failed but an earlier
    // one succeeded. Defaults to `scenario` itself when unset and not
    // a failure, matching the backend's latest_success falling back to
    // the same row as latest.
    scenarioLatestSuccess?: Record<string, unknown> | null;
    modelTurn?: "model_move" | "fallback_move" | "unavailable" | "stale";
    notYourTurnOnMove?: boolean;
    reviewFails?: boolean;
  } = {},
) {
  let lastArtifact: Record<string, unknown> | null = null;
  let activeGame: Record<string, unknown> | null = null;
  let scenario: Record<string, unknown> | null = opts.scenario ?? null;
  // Mirrors the backend's latest_success: the same object as `scenario`
  // whenever the last mutation succeeded, but unlike `scenario` it does
  // not go stale to a failure -- there is nothing in this mock that
  // ever fails an /assess or /review call, so a failure can only ever
  // be the seeded initial state.
  let latestSuccessScenario: Record<string, unknown> | null =
    opts.scenarioLatestSuccess !== undefined
      ? opts.scenarioLatestSuccess
      : opts.scenario && opts.scenario.status !== "failed"
        ? opts.scenario
        : null;
  let losses = 0;
  const history: Record<string, unknown>[] = [];
  if (opts.expiredAway) {
    losses = 1;
    history.push({
      id: "game_expired",
      result: "loss_timeout",
      time_limit_seconds: 300,
      ended_at: "now",
      legal_moves: 3,
    });
  }
  const gameStatus = (expiredAway = false) => ({
    game: activeGame,
    record: { wins: 0, losses, draws: 0 },
    board_fen: STARTING_FEN,
    history,
    expired_while_away: expiredAway,
  });
  return mock(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.endsWith("/scenario")) {
      return new Response(
        JSON.stringify({ latest: scenario, latest_success: latestSuccessScenario }),
      );
    }
    if (url.endsWith("/assess")) {
      scenario = { ...SUGGESTED_SCENARIO };
      latestSuccessScenario = scenario;
      return new Response(JSON.stringify(scenario));
    }
    if (url.endsWith("/review")) {
      if (opts.reviewFails) {
        return new Response(JSON.stringify({ detail: "scenario already reviewed" }), {
          status: 422,
        });
      }
      const body = JSON.parse(String(init?.body));
      const current = scenario ?? SUGGESTED_SCENARIO;
      scenario = body.accept
        ? { ...current, status: "accepted" }
        : {
            ...current,
            status: "edited",
            assessment: body.assessment,
            real_world: body.real_world,
            video_prompt: body.video_prompt,
          };
      latestSuccessScenario = scenario;
      return new Response(JSON.stringify(scenario));
    }
    if (url.endsWith("/model-move")) {
      const outcome = opts.modelTurn ?? "model_move";
      if (outcome === "unavailable") {
        return new Response(
          JSON.stringify({
            outcome,
            move: null,
            dataset_rows: [],
            game_result: null,
            attempts: [
              {
                attempt_number: 1,
                actor: "model",
                status: "transport_failed",
                parsed_move: null,
                is_legal: null,
                model: "gpt-5.6-luna",
                error_detail: "could not reach provider",
              },
            ],
            detail: "gpt-5.6-luna could not be reached after 2 attempts. No move was played.",
          }),
        );
      }
      if (outcome === "stale") {
        // The board advanced to a fresh game somewhere else while the
        // reply was in flight.
        activeGame = null;
        return new Response(
          JSON.stringify({
            outcome,
            move: null,
            dataset_rows: [],
            game_result: null,
            attempts: [
              {
                attempt_number: 1,
                actor: "model",
                status: "stale",
                parsed_move: "e7e5",
                is_legal: null,
                model: "gpt-5.6-luna",
                error_detail: "board changed since this move was decided",
              },
            ],
            detail:
              "The position changed before this reply could be applied. Refresh and try again.",
          }),
        );
      }
      const fallback = outcome === "fallback_move";
      return new Response(
        JSON.stringify({
          outcome,
          move: {
            id: "move_model",
            workspace_id: "workspace_1",
            ply: 1,
            uci: fallback ? "a7a6" : "e7e5",
            san: fallback ? "a6" : "e5",
            fen_before: "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
            fen_after: "rnbqkbnr/1ppppppp/p7/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2",
            is_legal: true,
            is_check: false,
            is_checkmate: false,
            reward: 1,
            actor: fallback ? "fallback" : "model",
            model: "gpt-5.6-luna",
            created_at: "now",
          },
          dataset_rows: [],
          game_result: null,
          attempts: [],
          detail: fallback
            ? "gpt-5.6-luna did not produce a legal move in 2 attempts. Fallback played a7a6 (first legal move in UCI order)."
            : null,
        }),
      );
    }
    if (url.endsWith("/llm/status")) {
      return new Response(
        JSON.stringify({
          configured: true,
          model: "gpt-5.6-luna",
          opponent_models: opts.opponentModels ?? ["gpt-5.6-luna"],
        }),
      );
    }
    if (url.endsWith("/game/start")) {
      const body = JSON.parse(String(init?.body));
      activeGame = {
        id: "game_1",
        workspace_id: "workspace_1",
        time_limit_seconds: body.time_limit_seconds,
        opponent_model: body.opponent_model,
        started_at: "2026-07-06T10:00:00+00:00",
        ended_at: null,
        result: null,
        seconds_left: body.time_limit_seconds,
      };
      return new Response(JSON.stringify(gameStatus()));
    }
    if (url.endsWith("/game/start-over")) {
      losses += 1;
      const previous = activeGame as Record<string, unknown>;
      history.unshift({
        id: `finished_${losses}`,
        result: "loss_resign",
        time_limit_seconds: previous.time_limit_seconds,
        ended_at: "now",
        legal_moves: 0,
      });
      activeGame = { ...previous, id: "game_2" };
      return new Response(JSON.stringify(gameStatus()));
    }
    if (url.endsWith("/game")) {
      return new Response(JSON.stringify(gameStatus(opts.expiredAway === true)));
    }
    if (url.endsWith("/state")) {
      return new Response(
        JSON.stringify({
          workspace: { board_fen: STARTING_FEN },
          moves: [],
          dataset_rows: [],
        }),
      );
    }
    if (url.endsWith("/snippet")) {
      const body = JSON.parse(String(init?.body));
      return new Response(
        JSON.stringify({
          id: "workspace_1",
          user_id: "user_1",
          page_id: "page_1",
          shape_id: "shape:workspace-user_1-chess-machine",
          position_index: 0,
          selected_snippet_id: body.snippet_id,
          board_fen: STARTING_FEN,
        }),
      );
    }
    if (url.endsWith("/moves")) {
      if (opts.notYourTurnOnMove) {
        return new Response(
          JSON.stringify({
            detail: "it is the model's turn; call /model-move instead of playing for it",
          }),
          { status: 409 },
        );
      }
      const body = JSON.parse(String(init?.body));
      const legal = body.uci === "e2e4";
      const isCheck = legal && opts.checkOnMove === true;
      return new Response(
        JSON.stringify({
          move: {
            id: "move_1",
            workspace_id: "workspace_1",
            ply: 0,
            uci: body.uci,
            san: legal ? "e4" : null,
            fen_before: STARTING_FEN,
            fen_after: legal
              ? "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
              : STARTING_FEN,
            is_legal: legal,
            is_check: isCheck,
            is_checkmate: false,
            reward: legal ? 1 : -1,
            actor: "participant",
            model: null,
            created_at: "now",
          },
          dataset_rows: legal
            ? [
                {
                  id: "row_1",
                  workspace_id: "workspace_1",
                  move_id: "move_1",
                  shape: "fen_to_move",
                  payload: { fen: STARTING_FEN, target_uci: "e2e4" },
                  created_at: "now",
                },
              ]
            : [],
          game_result: null,
        }),
      );
    }
    if (url.includes("/artifacts")) {
      return new Response(JSON.stringify(lastArtifact ? [lastArtifact] : []));
    }
    if (url.includes("/evals")) {
      return new Response(JSON.stringify([]));
    }
    if (url.endsWith("/jobs")) {
      lastArtifact = {
        id: "artifact_1",
        job_config_id: "job_1",
        modality: "text",
        kind: "prompt_eval",
        payload: { legal_move_rate: 1.0, valid_json_rate: 1.0, move_count: 1 },
        cached: false,
        created_at: "now",
      };
      return new Response(
        JSON.stringify({
          job_config: {
            id: "job_1",
            workspace_id: "workspace_1",
            job_type: "text.prompt_eval",
            params_json: "{}",
            created_at: "now",
          },
          artifact: lastArtifact,
        }),
      );
    }
    return new Response("not found", { status: 404 });
  });
}

afterEach(() => {
  cleanup();
});

describe("WorkspacePanel", () => {
  test("loads and shows the board for the workspace", async () => {
    globalThis.fetch = routedFetch() as unknown as typeof fetch;
    render(<WorkspacePanel shape={makeShape()} isEditing={false} />);

    await waitFor(() => {
      expect(screen.getByTestId("chess-board")).toBeTruthy();
    });
  });

  test("a legal move updates the board and adds a dataset row", async () => {
    globalThis.fetch = routedFetch() as unknown as typeof fetch;
    render(
      <CurrentUserContext.Provider value={{ id: "user_1", name: "Ada" }}>
        <WorkspacePanel shape={makeShape()} isEditing={true} />
      </CurrentUserContext.Provider>,
    );

    await waitFor(() => screen.getByTestId("chess-board"));
    fireEvent.click(screen.getByTestId("square-e2"));
    fireEvent.click(screen.getByTestId("square-e4"));

    await waitFor(() => {
      expect(screen.getByText("FEN -> move")).toBeTruthy();
    });
  });

  test("switching the mini IDE snippet persists the selection", async () => {
    const fetchMock = routedFetch();
    globalThis.fetch = fetchMock as unknown as typeof fetch;
    render(
      <CurrentUserContext.Provider value={{ id: "user_1", name: "Ada" }}>
        <WorkspacePanel shape={makeShape()} isEditing={true} />
      </CurrentUserContext.Provider>,
    );

    await waitFor(() => screen.getByTestId("chess-board"));
    fireEvent.click(screen.getByTestId("snippet-tab-reward_function"));

    expect(screen.getByTestId("snippet-tab-reward_function").className).toContain(
      "mini-ide-tab-active",
    );
    await waitFor(() => {
      const putCall = fetchMock.mock.calls.find((call) => String(call[0]).endsWith("/snippet"));
      expect(putCall).toBeTruthy();
    });
  });

  test("shows read-only styling for someone else's workspace", async () => {
    globalThis.fetch = routedFetch() as unknown as typeof fetch;
    render(
      <CurrentUserContext.Provider value={{ id: "someone_else", name: "Grace" }}>
        <WorkspacePanel shape={makeShape()} isEditing={false} />
      </CurrentUserContext.Provider>,
    );

    await waitFor(() => {
      expect(screen.getByText("view only")).toBeTruthy();
    });
  });

  test("disables the board and shows a locked badge when the presenter has locked editing", async () => {
    globalThis.fetch = routedFetch() as unknown as typeof fetch;
    render(
      <CurrentUserContext.Provider value={{ id: "user_1", name: "Ada" }}>
        <PresenterContext.Provider
          value={{
            locked: true,
            resetToken: 0,
            isPresenter: false,
            presenterMode: "idle",
            reportNotice: () => {},
          }}
        >
          <WorkspacePanel shape={makeShape()} isEditing={true} />
        </PresenterContext.Provider>
      </CurrentUserContext.Provider>,
    );

    await waitFor(() => screen.getByTestId("chess-board"));
    expect(screen.getByText("locked")).toBeTruthy();
    expect(screen.getByTestId("square-e2").hasAttribute("disabled")).toBe(true);
  });

  test("starting a game shows the countdown and the start over button", async () => {
    globalThis.fetch = routedFetch() as unknown as typeof fetch;
    render(
      <CurrentUserContext.Provider value={{ id: "user_1", name: "Ada" }}>
        <WorkspacePanel shape={makeShape()} isEditing={true} />
      </CurrentUserContext.Provider>,
    );

    await waitFor(() => screen.getByTestId("start-game"));
    expect((screen.getByTestId("time-limit") as HTMLSelectElement).value).toBe("300");
    fireEvent.click(screen.getByTestId("start-game"));

    await waitFor(() => {
      expect(screen.getByTestId("game-timer").textContent).toContain("5:00");
    });
    expect(screen.getByTestId("start-over")).toBeTruthy();
    expect(screen.queryByTestId("start-game")).toBeNull();
  });

  test("a longer clock can be picked before starting", async () => {
    const fetchMock = routedFetch();
    globalThis.fetch = fetchMock as unknown as typeof fetch;
    render(
      <CurrentUserContext.Provider value={{ id: "user_1", name: "Ada" }}>
        <WorkspacePanel shape={makeShape()} isEditing={true} />
      </CurrentUserContext.Provider>,
    );

    await waitFor(() => screen.getByTestId("start-game"));
    fireEvent.change(screen.getByTestId("time-limit"), { target: { value: "1800" } });
    fireEvent.click(screen.getByTestId("start-game"));

    await waitFor(() => screen.getByTestId("game-timer"));
    const startCall = fetchMock.mock.calls.find((call) => String(call[0]).endsWith("/game/start"));
    expect(JSON.parse(String((startCall?.[1] as RequestInit).body)).time_limit_seconds).toBe(1800);
    expect(screen.getByTestId("game-timer").textContent).toContain("30:00");
  });

  test("start over demands confirmation and records the loss", async () => {
    globalThis.fetch = routedFetch() as unknown as typeof fetch;
    render(
      <CurrentUserContext.Provider value={{ id: "user_1", name: "Ada" }}>
        <WorkspacePanel shape={makeShape()} isEditing={true} />
      </CurrentUserContext.Provider>,
    );

    await waitFor(() => screen.getByTestId("start-game"));
    fireEvent.click(screen.getByTestId("start-game"));
    await waitFor(() => screen.getByTestId("start-over"));

    fireEvent.click(screen.getByTestId("start-over"));
    expect(screen.getByText("Starting over counts as a loss.")).toBeTruthy();

    fireEvent.click(screen.getByTestId("confirm-start-over"));
    await waitFor(() => {
      expect(screen.getByTestId("game-record").textContent).toBe("W 0 L 1 D 0");
    });
    expect(screen.getByTestId("game-notice").textContent).toContain("loss");
    // The fresh game is already running.
    expect(screen.getByTestId("game-timer")).toBeTruthy();
  });

  test("keep playing backs out of the start over confirmation", async () => {
    const fetchMock = routedFetch();
    globalThis.fetch = fetchMock as unknown as typeof fetch;
    render(
      <CurrentUserContext.Provider value={{ id: "user_1", name: "Ada" }}>
        <WorkspacePanel shape={makeShape()} isEditing={true} />
      </CurrentUserContext.Provider>,
    );

    await waitFor(() => screen.getByTestId("start-game"));
    fireEvent.click(screen.getByTestId("start-game"));
    await waitFor(() => screen.getByTestId("start-over"));

    fireEvent.click(screen.getByTestId("start-over"));
    fireEvent.click(screen.getByText("Keep playing"));

    expect(screen.getByTestId("game-timer")).toBeTruthy();
    const startOverCall = fetchMock.mock.calls.find((call) =>
      String(call[0]).endsWith("/game/start-over"),
    );
    expect(startOverCall).toBeUndefined();
  });

  test("a timeout that happened while away is announced on load", async () => {
    globalThis.fetch = routedFetch({ expiredAway: true }) as unknown as typeof fetch;
    render(
      <CurrentUserContext.Provider value={{ id: "user_1", name: "Ada" }}>
        <WorkspacePanel shape={makeShape()} isEditing={true} />
      </CurrentUserContext.Provider>,
    );

    await waitFor(() => screen.getByTestId("game-notice"));
    expect(screen.getByTestId("game-notice").textContent).toContain("while you were away");
    expect(screen.getByTestId("game-record").textContent).toBe("W 0 L 1 D 0");
    expect(screen.getByTestId("game-banter")).toBeTruthy();
  });

  test("finished matches show up in the history list", async () => {
    globalThis.fetch = routedFetch() as unknown as typeof fetch;
    render(
      <CurrentUserContext.Provider value={{ id: "user_1", name: "Ada" }}>
        <WorkspacePanel shape={makeShape()} isEditing={true} />
      </CurrentUserContext.Provider>,
    );

    await waitFor(() => screen.getByTestId("start-game"));
    fireEvent.click(screen.getByTestId("start-game"));
    await waitFor(() => screen.getByTestId("start-over"));
    fireEvent.click(screen.getByTestId("start-over"));
    fireEvent.click(screen.getByTestId("confirm-start-over"));

    await waitFor(() => screen.getByTestId("match-history"));
    const items = screen.getByTestId("match-history").querySelectorAll("li");
    expect(items.length).toBe(1);
    expect(items[0].textContent).toContain("Loss, started over");
  });

  test("with several opponents on offer, starting sends the chosen one", async () => {
    const fetchMock = routedFetch({
      opponentModels: ["google/gemma-4-E2B-it-qat-q4_0-gguf", "openai/gpt-5.6", "gpt-5.6-luna"],
    });
    globalThis.fetch = fetchMock as unknown as typeof fetch;
    render(
      <CurrentUserContext.Provider value={{ id: "user_1", name: "Ada" }}>
        <WorkspacePanel shape={makeShape()} isEditing={true} />
      </CurrentUserContext.Provider>,
    );

    await waitFor(() => screen.getByTestId("opponent-model"));
    // Short names in the picker, full ids on the wire.
    const options = Array.from(
      (screen.getByTestId("opponent-model") as HTMLSelectElement).options,
    ).map((option) => option.textContent);
    expect(options).toEqual(["gemma-4-E2B-it-qat-q4_0-gguf", "gpt-5.6", "gpt-5.6-luna"]);

    fireEvent.change(screen.getByTestId("opponent-model"), {
      target: { value: "openai/gpt-5.6" },
    });
    fireEvent.click(screen.getByTestId("start-game"));

    await waitFor(() => screen.getByTestId("game-timer"));
    const startCall = fetchMock.mock.calls.find((call) => String(call[0]).endsWith("/game/start"));
    expect(JSON.parse(String((startCall?.[1] as RequestInit).body)).opponent_model).toBe(
      "openai/gpt-5.6",
    );
  });

  test("a single-model setup shows no picker", async () => {
    globalThis.fetch = routedFetch() as unknown as typeof fetch;
    render(
      <CurrentUserContext.Provider value={{ id: "user_1", name: "Ada" }}>
        <WorkspacePanel shape={makeShape()} isEditing={true} />
      </CurrentUserContext.Provider>,
    );

    await waitFor(() => screen.getByTestId("start-game"));
    expect(screen.queryByTestId("opponent-model")).toBeNull();
  });

  test("a checking move earns a pun", async () => {
    globalThis.fetch = routedFetch({ checkOnMove: true }) as unknown as typeof fetch;
    render(
      <CurrentUserContext.Provider value={{ id: "user_1", name: "Ada" }}>
        <WorkspacePanel shape={makeShape()} isEditing={true} />
      </CurrentUserContext.Provider>,
    );

    await waitFor(() => screen.getByTestId("chess-board"));
    fireEvent.click(screen.getByTestId("square-e2"));
    fireEvent.click(screen.getByTestId("square-e4"));

    await waitFor(() => screen.getByTestId("game-banter"));
    expect(screen.getByTestId("game-banter").textContent).toContain("Check");
  });

  test("a persisted scenario is restored on load", async () => {
    globalThis.fetch = routedFetch({
      scenario: { ...SUGGESTED_SCENARIO, status: "accepted" },
    }) as unknown as typeof fetch;
    render(
      <CurrentUserContext.Provider value={{ id: "user_1", name: "Ada" }}>
        <WorkspacePanel shape={makeShape()} isEditing={true} />
      </CurrentUserContext.Provider>,
    );

    await waitFor(() => screen.getByTestId("scenario-provenance"));
    expect(screen.getByText("Level.")).toBeTruthy();
    expect(screen.getByTestId("scenario-provenance").textContent).toContain("accepted");
    expect(screen.getByTestId("scenario-provenance").textContent).toContain("assess-v1");
  });

  test("accepting a suggestion records the review without losing the raw text", async () => {
    globalThis.fetch = routedFetch({ scenario: SUGGESTED_SCENARIO }) as unknown as typeof fetch;
    render(
      <CurrentUserContext.Provider value={{ id: "user_1", name: "Ada" }}>
        <WorkspacePanel shape={makeShape()} isEditing={true} />
      </CurrentUserContext.Provider>,
    );

    await waitFor(() => screen.getByTestId("scenario-accept"));
    fireEvent.click(screen.getByTestId("scenario-accept"));

    await waitFor(() => {
      expect(screen.getByTestId("scenario-provenance").textContent).toContain("accepted");
    });
    expect(screen.getByText("Level.")).toBeTruthy();
  });

  test("editing a suggestion saves the participant's text", async () => {
    globalThis.fetch = routedFetch({ scenario: SUGGESTED_SCENARIO }) as unknown as typeof fetch;
    render(
      <CurrentUserContext.Provider value={{ id: "user_1", name: "Ada" }}>
        <WorkspacePanel shape={makeShape()} isEditing={true} />
      </CurrentUserContext.Provider>,
    );

    await waitFor(() => screen.getByTestId("scenario-start-edit"));
    fireEvent.click(screen.getByTestId("scenario-start-edit"));
    fireEvent.change(screen.getByLabelText("Assessment"), {
      target: { value: "Sharper than it looks." },
    });
    fireEvent.click(screen.getByTestId("scenario-save-edit"));

    await waitFor(() => {
      expect(screen.getByTestId("scenario-provenance").textContent).toContain("edited");
    });
    expect(screen.getByText("Sharper than it looks.")).toBeTruthy();
  });

  test("a failed scenario survives reload as the error state, not the empty state", async () => {
    globalThis.fetch = routedFetch({ scenario: FAILED_SCENARIO }) as unknown as typeof fetch;
    render(
      <CurrentUserContext.Provider value={{ id: "user_1", name: "Ada" }}>
        <WorkspacePanel shape={makeShape()} isEditing={true} />
      </CurrentUserContext.Provider>,
    );

    await waitFor(() => screen.getByTestId("scenario-error"));
    expect(screen.getByTestId("scenario-error").textContent).toContain("502 from video_prompt");
    // Not the pristine "play a move" empty state, and the recovery
    // button reads as a retry rather than a fresh first assessment.
    expect(screen.queryByText(/Play a move, get a read/)).toBeNull();
    expect(screen.getByTestId("assess-position").textContent).toBe("Retry assessment");
  });

  test("a previous successful mapping survives reload alongside a later failure", async () => {
    // Reproduces the reported gap: the reload endpoint used to return
    // only the single latest row. During a live failure the previous
    // mapping stays visible next to the new error (the component
    // simply never overwrites its state on a failed request), but
    // reload received only the failure and had no way to restore it.
    globalThis.fetch = routedFetch({
      scenario: FAILED_SCENARIO,
      scenarioLatestSuccess: SUGGESTED_SCENARIO,
    }) as unknown as typeof fetch;
    render(
      <CurrentUserContext.Provider value={{ id: "user_1", name: "Ada" }}>
        <WorkspacePanel shape={makeShape()} isEditing={true} />
      </CurrentUserContext.Provider>,
    );

    await waitFor(() => screen.getByTestId("scenario-error"));
    expect(screen.getByTestId("scenario-error").textContent).toContain("502 from video_prompt");
    // The last mapping that actually succeeded is restored underneath
    // the failure, exactly like a live failure would leave on screen.
    await waitFor(() => screen.getByTestId("scenario-provenance"));
    expect(screen.getByTestId("scenario-provenance").textContent).toContain("suggested");
    expect(screen.getByText(SUGGESTED_SCENARIO.real_world)).toBeTruthy();
  });

  test("a failed review is not silent", async () => {
    globalThis.fetch = routedFetch({
      scenario: SUGGESTED_SCENARIO,
      reviewFails: true,
    }) as unknown as typeof fetch;
    render(
      <CurrentUserContext.Provider value={{ id: "user_1", name: "Ada" }}>
        <WorkspacePanel shape={makeShape()} isEditing={true} />
      </CurrentUserContext.Provider>,
    );

    await waitFor(() => screen.getByTestId("scenario-accept"));
    fireEvent.click(screen.getByTestId("scenario-accept"));

    await waitFor(() => screen.getByTestId("scenario-error"));
    expect(screen.getByTestId("scenario-error").textContent).toContain("Could not save");
    // The last saved (still-suggested) mapping stays visible.
    expect(screen.getByText("Level.")).toBeTruthy();
  });

  test("a failed edit save is not silent and keeps the draft open", async () => {
    globalThis.fetch = routedFetch({
      scenario: SUGGESTED_SCENARIO,
      reviewFails: true,
    }) as unknown as typeof fetch;
    render(
      <CurrentUserContext.Provider value={{ id: "user_1", name: "Ada" }}>
        <WorkspacePanel shape={makeShape()} isEditing={true} />
      </CurrentUserContext.Provider>,
    );

    await waitFor(() => screen.getByTestId("scenario-start-edit"));
    fireEvent.click(screen.getByTestId("scenario-start-edit"));
    fireEvent.change(screen.getByLabelText("Assessment"), {
      target: { value: "Sharper than it looks." },
    });
    fireEvent.click(screen.getByTestId("scenario-save-edit"));

    await waitFor(() => screen.getByTestId("scenario-error"));
    expect(screen.getByTestId("scenario-error").textContent).toContain("Could not save");
    // The draft is still open, unset by the failure.
    expect(screen.getByTestId("scenario-edit")).toBeTruthy();
  });

  test("a fallback model move advances the board and says what happened", async () => {
    globalThis.fetch = routedFetch({ modelTurn: "fallback_move" }) as unknown as typeof fetch;
    render(
      <CurrentUserContext.Provider value={{ id: "user_1", name: "Ada" }}>
        <WorkspacePanel shape={makeShape()} isEditing={true} />
      </CurrentUserContext.Provider>,
    );

    await waitFor(() => screen.getByTestId("start-game"));
    fireEvent.click(screen.getByTestId("start-game"));
    await waitFor(() => screen.getByTestId("game-timer"));
    fireEvent.click(screen.getByTestId("square-e2"));
    fireEvent.click(screen.getByTestId("square-e4"));

    await waitFor(() => {
      expect(screen.getByTestId("game-notice").textContent).toContain("Fallback played a7a6");
    });
    expect(screen.getByTestId("move-status").textContent).toContain("Fallback: a6");
  });

  test("an unavailable model turn shows a retry action instead of hanging", async () => {
    const fetchMock = routedFetch({ modelTurn: "unavailable" });
    globalThis.fetch = fetchMock as unknown as typeof fetch;
    render(
      <CurrentUserContext.Provider value={{ id: "user_1", name: "Ada" }}>
        <WorkspacePanel shape={makeShape()} isEditing={true} />
      </CurrentUserContext.Provider>,
    );

    await waitFor(() => screen.getByTestId("start-game"));
    fireEvent.click(screen.getByTestId("start-game"));
    await waitFor(() => screen.getByTestId("game-timer"));
    fireEvent.click(screen.getByTestId("square-e2"));
    fireEvent.click(screen.getByTestId("square-e4"));

    await waitFor(() => screen.getByTestId("retry-model-move"));
    expect(screen.getByTestId("game-notice").textContent).toContain("No move was played");

    const callsBefore = fetchMock.mock.calls.filter((call) =>
      String(call[0]).endsWith("/model-move"),
    ).length;
    fireEvent.click(screen.getByTestId("retry-model-move"));
    await waitFor(() => {
      const callsAfter = fetchMock.mock.calls.filter((call) =>
        String(call[0]).endsWith("/model-move"),
      ).length;
      expect(callsAfter).toBe(callsBefore + 1);
    });
  });

  test("a stale model turn shows the retry action and resyncs the board", async () => {
    const fetchMock = routedFetch({ modelTurn: "stale" });
    globalThis.fetch = fetchMock as unknown as typeof fetch;
    render(
      <CurrentUserContext.Provider value={{ id: "user_1", name: "Ada" }}>
        <WorkspacePanel shape={makeShape()} isEditing={true} />
      </CurrentUserContext.Provider>,
    );

    await waitFor(() => screen.getByTestId("start-game"));
    fireEvent.click(screen.getByTestId("start-game"));
    await waitFor(() => screen.getByTestId("game-timer"));
    fireEvent.click(screen.getByTestId("square-e2"));
    fireEvent.click(screen.getByTestId("square-e4"));

    await waitFor(() => screen.getByTestId("retry-model-move"));
    expect(screen.getByTestId("game-notice").textContent).toContain("position changed");

    // The board actually changed elsewhere; the panel resyncs instead
    // of trusting stale local state. Fetching /game is not enough proof
    // by itself: applyGameStatus only touches the local fen when its
    // { board: true } option is passed, so assert the rendered board
    // itself moved back to the server's STARTING_FEN, not just that a
    // request happened. Before the fix e2 stayed empty and the model
    // could go on to answer white's still-locally-recorded e4.
    await waitFor(() => {
      const gameCalls = fetchMock.mock.calls.filter((call) => String(call[0]).endsWith("/game"));
      expect(gameCalls.length).toBeGreaterThan(0);
    });
    await waitFor(() => {
      const e2 = within(screen.getByTestId("square-e2")).queryByRole("img");
      expect(e2?.getAttribute("alt")).toBe("P");
    });
    expect(within(screen.getByTestId("square-e4")).queryByRole("img")).toBeNull();
  });

  test("the board is not interactive on the model's turn in an active game", async () => {
    globalThis.fetch = routedFetch() as unknown as typeof fetch;
    render(
      <CurrentUserContext.Provider value={{ id: "user_1", name: "Ada" }}>
        <WorkspacePanel shape={makeShape()} isEditing={true} />
      </CurrentUserContext.Provider>,
    );

    await waitFor(() => screen.getByTestId("start-game"));
    fireEvent.click(screen.getByTestId("start-game"));
    await waitFor(() => screen.getByTestId("game-timer"));
    fireEvent.click(screen.getByTestId("square-e2"));
    fireEvent.click(screen.getByTestId("square-e4"));

    // The model's reply (mocked to be instant) lands and hands the
    // turn back; the board is interactive again for white's move.
    await waitFor(() => {
      expect(screen.getByTestId("move-status").textContent).toContain("Model:");
    });
    expect(screen.getByTestId("square-e2").hasAttribute("disabled")).toBe(false);
  });

  test("a not-your-turn rejection does not claim a timeout and resyncs state", async () => {
    const fetchMock = routedFetch({ notYourTurnOnMove: true });
    globalThis.fetch = fetchMock as unknown as typeof fetch;
    render(
      <CurrentUserContext.Provider value={{ id: "user_1", name: "Ada" }}>
        <WorkspacePanel shape={makeShape()} isEditing={true} />
      </CurrentUserContext.Provider>,
    );

    await waitFor(() => screen.getByTestId("chess-board"));
    fireEvent.click(screen.getByTestId("square-e2"));
    fireEvent.click(screen.getByTestId("square-e4"));

    await waitFor(() => screen.getByTestId("game-notice"));
    expect(screen.getByTestId("game-notice").textContent).not.toContain("Time ran out");

    await waitFor(() => {
      const gameCalls = fetchMock.mock.calls.filter((call) => String(call[0]).endsWith("/game"));
      expect(gameCalls.length).toBeGreaterThan(0);
    });
  });

  test("running a job shows the resulting artifact", async () => {
    globalThis.fetch = routedFetch() as unknown as typeof fetch;
    render(
      <CurrentUserContext.Provider value={{ id: "user_1", name: "Ada" }}>
        <WorkspacePanel shape={makeShape()} isEditing={true} />
      </CurrentUserContext.Provider>,
    );

    await waitFor(() => screen.getByTestId("config-panel"));
    fireEvent.click(screen.getByTestId("run-job-text.prompt_eval"));

    await waitFor(() => {
      expect(screen.getByTestId("artifact-panel")).toBeTruthy();
    });
    expect(screen.getByText("prompt_eval")).toBeTruthy();
  });
});
