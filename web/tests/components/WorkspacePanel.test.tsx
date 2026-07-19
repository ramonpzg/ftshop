import { afterEach, describe, expect, mock, test } from "bun:test";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
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

function routedFetch(
  opts: { expiredAway?: boolean; checkOnMove?: boolean; opponentModels?: string[] } = {},
) {
  let lastArtifact: Record<string, unknown> | null = null;
  let activeGame: Record<string, unknown> | null = null;
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
        <PresenterContext.Provider value={{ locked: true, resetToken: 0, isPresenter: false }}>
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
