"""The interactive loop: render one screen, read one line, dispatch.
Typed moves and terse commands only; no function keys, mouse, or key
chords, because phone keyboards make typed input the reliable path.

The loop owns which screen is visible and delegates everything else:
move legality to calculations, game orchestration to actions, rendering
to screens. One model call is in flight at a time, with a visible
waiting state; every failure leaves the board unchanged and offers
retry."""

import sqlite3
from contextlib import nullcontext

import chess
from rich.console import Console
from rich.text import Text

from chess_tui.actions import replay as replay_actions
from chess_tui.actions.game import (
    GameState,
    TurnFailure,
    apply_participant_move,
    play_model_turn,
    start_game,
)
from chess_tui.calculations.commands import Command, MoveText, parse_input
from chess_tui.calculations.moves import MoveRejection, parse_participant_move
from chess_tui.calculations.stats import compute_record
from chess_tui.data import games_repo, plies_repo
from chess_tui.data.config import Config
from chess_tui.data.llm_client import LlmClient
from chess_tui.ui.screens import (
    GameView,
    game_screen,
    help_screen,
    history_screen,
    home_screen,
    move_label,
    replay_screen,
)
from chess_tui.ui.theme import pick_theme

_FAILURE_HEADLINES = {
    "invalid_reply": "Gemma did not return a legal move. retry or quit",
    "unreachable": "server unreachable. retry or quit",
    "timeout": "Gemma timed out. retry or quit",
    "http_error": "server error. retry or quit",
    "canceled": "model call canceled. retry or quit",
}


class App:
    def __init__(
        self,
        config: Config,
        conn: sqlite3.Connection,
        client: LlmClient,
        console: Console | None = None,
        input_fn=None,
    ) -> None:
        self.config = config
        self.conn = conn
        self.client = client
        self.console = console or Console(
            no_color=True if config.no_color else None, highlight=False
        )
        self.theme = pick_theme(config.no_color)
        self.input_fn = input_fn or (lambda: input("> "))
        self.screen = "home"
        self.game: GameState | None = None
        self.cursor: replay_actions.ReplayCursor | None = None
        self.flipped = False
        self.notice: str | None = None
        self.help_return = "home"
        self.history: list[replay_actions.HistoryItem] = []

    def run(self) -> None:
        while True:
            self._render()
            try:
                line = self.input_fn()
            except (EOFError, KeyboardInterrupt):
                break
            if not self._dispatch(line):
                break

    # Rendering

    def _render(self) -> None:
        self.console.clear()
        width = self.console.width
        if self.screen == "home":
            lines = home_screen(self._record(), self.config.model, self.theme, width)
        elif self.screen == "game":
            lines = game_screen(self._game_view(), self.theme, width)
        elif self.screen == "history":
            lines = history_screen(self.history, self.theme, width)
        elif self.screen == "replay":
            assert self.cursor is not None
            lines = replay_screen(self.cursor, self.flipped, self.theme, width)
        else:
            lines = help_screen(self.theme, width)
        if self.notice and self.screen != "game":
            lines.append(Text(""))
            lines.append(Text(self.notice, style=self.theme.bad))
        for line in lines:
            self.console.print(line, no_wrap=True, overflow="crop")

    def _record(self):
        return compute_record(
            games_repo.game_results(self.conn),
            plies_repo.participant_captures_by_game(self.conn),
        )

    def _game_view(self) -> GameView:
        game = self.game
        assert game is not None
        board = game.board
        last_uci = board.move_stack[-1].uci() if board.move_stack else None
        if game.sans:
            label = move_label(len(board.move_stack), game.sans[-1])
        else:
            label = "new game. your move"
        state_word, tone = self._state_word(game)
        failure = game.pending_failure
        return GameView(
            fen=board.fen(),
            flipped=self.flipped,
            move_number=board.fullmove_number,
            last_move_uci=last_uci,
            last_move_label=label,
            state_word=state_word,
            state_tone=tone,
            comment=game.last_comment,
            notice=self.notice,
            failure_headline=_FAILURE_HEADLINES[failure.code] if failure else None,
            failure_detail=failure.detail if failure else None,
            game_over=game.over,
        )

    def _state_word(self, game: GameState) -> tuple[str, str]:
        if game.over:
            who = {"1-0": ("white won", "good"), "0-1": ("black won", "bad")}
            outcome, tone = who.get(game.result or "", ("draw", "neutral"))
            return f"{game.termination}. {outcome}", tone
        if game.board.is_check():
            you_are_checked = game.board.turn == chess.WHITE
            return "check", "bad" if you_are_checked else "good"
        return "", "neutral"

    # Dispatch

    def _dispatch(self, line: str) -> bool:
        parsed = parse_input(line)
        if isinstance(parsed, MoveText):
            self._try_move(parsed.text)
            return True
        return self._run_command(parsed)

    def _run_command(self, command: Command) -> bool:
        kind = command.kind
        self.notice = None
        if kind == "blank":
            if self.screen == "replay" and self.cursor is not None:
                self.cursor.forward()
        elif kind == "new":
            self.game = start_game(self.conn, self.config.model)
            self.screen = "game"
        elif kind == "history":
            self.history = replay_actions.list_history(self.conn)
            self.screen = "history"
        elif kind == "replay":
            self._open_replay(command.arg)
        elif kind == "retry":
            if self.screen == "game" and self.game and self.game.pending_failure:
                self._model_turn()
            else:
                self.notice = "nothing to retry"
        elif kind == "flip":
            self.flipped = not self.flipped
        elif kind == "help":
            if self.screen != "help":
                self.help_return = self.screen
            self.screen = "help"
        elif kind == "next":
            if self.screen == "replay" and self.cursor is not None:
                self.cursor.forward()
        elif kind == "prev":
            if self.screen == "replay" and self.cursor is not None:
                self.cursor.back()
        elif kind == "quit":
            return self._quit()
        return True

    def _quit(self) -> bool:
        if self.screen == "home":
            return False
        if self.screen == "game":
            self.game = None
            self.screen = "home"
        elif self.screen == "history":
            self.screen = "home"
        elif self.screen == "replay":
            self.history = replay_actions.list_history(self.conn)
            self.screen = "history"
        else:
            self.screen = self.help_return
        return True

    def _open_replay(self, arg: int | None) -> None:
        self.history = replay_actions.list_history(self.conn)
        if not self.history:
            self.notice = "no games yet"
            return
        index = (arg or 1) - 1
        if index < 0 or index >= len(self.history):
            self.notice = f"no game {arg} in history"
            self.screen = "history"
            return
        cursor = replay_actions.open_replay(self.conn, self.history[index].game_id)
        if cursor is None:
            self.notice = "that game is gone"
            return
        self.cursor = cursor
        self.screen = "replay"

    def _try_move(self, text: str) -> None:
        if self.screen != "game" or self.game is None:
            self.notice = f"not a command: {text}. try help"
            return
        game = self.game
        if game.over:
            self.notice = "game over. new starts another"
            return
        if game.pending_failure is not None:
            self.notice = "waiting on Gemma. retry or quit"
            return
        if game.board.turn != chess.WHITE:
            self.notice = "not your turn"
            return
        parsed = parse_participant_move(game.board.fen(), text)
        if isinstance(parsed, MoveRejection):
            self.notice = parsed.detail
            return
        self.notice = None
        applied = apply_participant_move(self.conn, game, parsed)
        if not applied.game_over:
            self._model_turn()

    def _model_turn(self) -> None:
        game = self.game
        assert game is not None
        game.pending_failure = None
        self._render()
        waiting = Text("Gemma is choosing...", style=self.theme.accent)
        if self.console.is_terminal:
            context = self.console.status(waiting, spinner="line")
        else:
            self.console.print(waiting)
            context = nullcontext()
        with context:
            result = play_model_turn(self.conn, game, self.client)
        if isinstance(result, TurnFailure):
            return
        self.notice = None
