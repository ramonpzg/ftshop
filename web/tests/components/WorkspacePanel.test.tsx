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

function routedFetch() {
  let lastArtifact: Record<string, unknown> | null = null;
  let activeGame: Record<string, unknown> | null = null;
  let losses = 0;
  const gameStatus = () => ({
    game: activeGame,
    record: { wins: 0, losses, draws: 0 },
    board_fen: STARTING_FEN,
  });
  return mock(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.endsWith("/llm/status")) {
      return new Response(JSON.stringify({ configured: true, model: "gpt-5.5-mini" }));
    }
    if (url.endsWith("/game/start")) {
      const body = JSON.parse(String(init?.body));
      activeGame = {
        id: "game_1",
        workspace_id: "workspace_1",
        time_limit_seconds: body.time_limit_seconds,
        started_at: "2026-07-06T10:00:00+00:00",
        ended_at: null,
        result: null,
        seconds_left: body.time_limit_seconds,
      };
      return new Response(JSON.stringify(gameStatus()));
    }
    if (url.endsWith("/game/start-over")) {
      losses += 1;
      activeGame = { ...(activeGame as Record<string, unknown>), id: "game_2" };
      return new Response(JSON.stringify(gameStatus()));
    }
    if (url.endsWith("/game")) {
      return new Response(JSON.stringify(gameStatus()));
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
            is_check: false,
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
