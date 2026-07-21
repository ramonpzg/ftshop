"""The interactive loop: render one screen, read one line, dispatch.
Typed moves and slash commands only; no function keys, mouse, or key
chords, because phone keyboards make typed input the reliable path.

The loop runs inside the terminal's alternate screen buffer, the same
one vim and htop use, so frames never pollute scrollback and exiting
restores the shell exactly as it was. An active game survives visiting
help, history, or a replay; /back returns to it. One model call is in
flight at a time, with a visible waiting state; every failure leaves
the board unchanged and offers retry."""

import random
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
from chess_tui.calculations.commands import (
    Command,
    MoveText,
    UnknownCommand,
    command_suggestions,
    parse_input,
)
from chess_tui.calculations.moves import MoveRejection, parse_participant_move
from chess_tui.calculations.stats import compute_record
from chess_tui.data import games_repo, plies_repo, settings_repo
from chess_tui.data.config import Config
from chess_tui.data.llm_client import LlmClient
from chess_tui.data.settings_repo import PLAYER_NAME_KEY
from chess_tui.ui.input_line import read_line
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

# The exact copy the phase prompt fixed; bare words are valid commands
# so the line stays true and fits 48 columns.
_FAILURE_HEADLINES = {
    "invalid_reply": "Gemma did not return a legal move. retry or quit",
    "unreachable": "server unreachable. retry or quit",
    "timeout": "Gemma timed out. retry or quit",
    "http_error": "server error. retry or quit",
    "canceled": "model call canceled. retry or quit",
}

_DEFAULT_NAME = "player"


class App:
    def __init__(
        self,
        config: Config,
        conn: sqlite3.Connection,
        client: LlmClient,
        console: Console | None = None,
        input_fn=None,
        rng: random.Random | None = None,
    ) -> None:
        self.config = config
        self.conn = conn
        self.client = client
        self.console = console or Console(
            no_color=True if config.no_color else None, highlight=False
        )
        self.theme = pick_theme(config.no_color)
        self.input_fn = input_fn or (
            lambda: read_line("> ", command_suggestions, no_color=config.no_color)
        )
        self.rng = rng or random.Random()
        self.player_name = _DEFAULT_NAME
        self.screen = "home"
        self.game: GameState | None = None
        self.cursor: replay_actions.ReplayCursor | None = None
        self.flipped = False
        self.notice: str | None = None
        self.previous_screen = "home"
        self.history: list[replay_actions.HistoryItem] = []

    def run(self) -> None:
        use_alt_screen = self.console.is_terminal
        if use_alt_screen:
            self.console.set_alt_screen(True)
        try:
            self._resolve_player_name()
            while True:
                self._render()
                try:
                    line = self.input_fn()
                except (EOFError, KeyboardInterrupt):
                    break
                if not self._dispatch(line):
                    break
        finally:
            if use_alt_screen:
                self.console.set_alt_screen(False)

    # Player identity

    def _resolve_player_name(self) -> None:
        """Flag or env wins and is remembered; otherwise the stored
        name; otherwise ask once. Games recorded before names existed
        are claimed by the first name so the record stays continuous."""
        name = self.config.player_name or settings_repo.get_setting(self.conn, PLAYER_NAME_KEY)
        while not name:
            self.console.clear()
            self.console.print(Text("chess tui", style=f"bold {self.theme.ink}"))
            self.console.print(Text(""))
            self.console.print(Text("your name? it goes on the scoreboard", style=self.theme.soft))
            try:
                name = self.input_fn().strip() or _DEFAULT_NAME
            except (EOFError, KeyboardInterrupt):
                name = _DEFAULT_NAME
        self.player_name = name
        settings_repo.set_setting(self.conn, PLAYER_NAME_KEY, name)
        games_repo.claim_unnamed_games(self.conn, name)
        self.conn.commit()

    # Rendering

    def _render(self) -> None:
        self.console.clear()
        width = self.console.width
        height = self.console.size.height
        if self.screen == "home":
            lines = home_screen(
                self._record(),
                self.config.model,
                self.player_name,
                self.theme,
                width,
                game_in_progress=self.game is not None and not self.game.over,
            )
        elif self.screen == "game":
            lines = game_screen(self._game_view(), self.theme, width, height)
        elif self.screen == "history":
            lines = history_screen(self.history, self.theme, width)
        elif self.screen == "replay":
            assert self.cursor is not None
            lines = replay_screen(self.cursor, self.flipped, self.theme, width, height)
        else:
            lines = help_screen(self.theme, width)
        if self.notice and self.screen != "game":
            lines.append(Text(""))
            lines.append(Text(self.notice, style=self.theme.bad))
        for line in lines:
            self.console.print(line, no_wrap=True, overflow="crop")

    def _record(self):
        return compute_record(
            games_repo.game_results(self.conn, self.player_name),
            plies_repo.participant_captures_by_game(self.conn, self.player_name),
        )

    def _game_view(self) -> GameView:
        game = self.game
        assert game is not None
        board = game.board
        last_uci = board.move_stack[-1].uci() if board.move_stack else None
        if game.sans:
            label = move_label(len(board.move_stack), game.sans[-1])
        elif game.participant_color == chess.WHITE:
            label = "new game. your move"
        else:
            label = "new game. Gemma opens"
        state_word, tone = self._state_word(game)
        failure = game.pending_failure
        return GameView(
            fen=board.fen(),
            flipped=self.flipped,
            move_number=board.fullmove_number,
            player_label=f"{game.player_name}: {game.participant_color_name}",
            gemma_label=f"Gemma: {game.model_color_name}",
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
            if game.result == "1/2-1/2":
                return f"{game.termination}. draw", "neutral"
            white_won = game.result == "1-0"
            participant_won = white_won == (game.participant_color == chess.WHITE)
            winner = game.player_name if participant_won else "gemma"
            return f"{game.termination}. {winner} won", ("good" if participant_won else "bad")
        if game.board.is_check():
            you_are_checked = game.board.turn == game.participant_color
            return "check", "bad" if you_are_checked else "good"
        return "", "neutral"

    # Dispatch

    def _dispatch(self, line: str) -> bool:
        parsed = parse_input(line)
        if isinstance(parsed, MoveText):
            self._try_move(parsed.text)
            return True
        if isinstance(parsed, UnknownCommand):
            self.notice = f"unknown command {parsed.text}. /help lists them"
            return True
        return self._run_command(parsed)

    def _run_command(self, command: Command) -> bool:
        kind = command.kind
        self.notice = None
        if kind == "blank":
            if self.screen == "replay" and self.cursor is not None:
                self.cursor.forward()
        elif kind == "new":
            self._new_game()
        elif kind == "history":
            self._remember_screen()
            self.history = replay_actions.list_history(self.conn, self.player_name)
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
            self._remember_screen()
            self.screen = "help"
        elif kind == "back":
            self._go_back()
        elif kind == "next":
            if self.screen == "replay" and self.cursor is not None:
                self.cursor.forward()
        elif kind == "prev":
            if self.screen == "replay" and self.cursor is not None:
                self.cursor.back()
        elif kind == "quit":
            return self._quit()
        return True

    def _remember_screen(self) -> None:
        if self.screen not in ("help", "history", "replay"):
            self.previous_screen = self.screen

    def _go_back(self) -> None:
        if self.screen == "replay":
            self.screen = "history"
        elif self.screen in ("help", "history"):
            self.screen = (
                self.previous_screen if self._screen_exists(self.previous_screen) else "home"
            )
        elif self.game is not None:
            self.screen = "game"
        else:
            self.screen = "home"

    def _screen_exists(self, screen: str) -> bool:
        if screen == "game":
            return self.game is not None
        if screen == "replay":
            return self.cursor is not None
        return True

    def _quit(self) -> bool:
        if self.screen == "home":
            return False
        if self.screen == "game":
            # The game object stays; /back resumes it from home.
            self.screen = "home"
        elif self.screen == "replay":
            self.screen = "history"
        else:
            self.screen = (
                self.previous_screen if self._screen_exists(self.previous_screen) else "home"
            )
            if self.screen in ("help", "history"):
                self.screen = "home"
        return True

    def _new_game(self) -> None:
        color = chess.WHITE if self.rng.random() < 0.5 else chess.BLACK
        self.game = start_game(self.conn, self.config.model, color, self.player_name)
        self.flipped = color == chess.BLACK
        self.screen = "game"
        if self.game.model_to_move:
            self._model_turn()

    def _open_replay(self, arg: int | None) -> None:
        self.history = replay_actions.list_history(self.conn, self.player_name)
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
        self._remember_screen()
        self.cursor = cursor
        self.flipped = cursor.participant_color == "black"
        self.screen = "replay"

    def _try_move(self, text: str) -> None:
        if self.screen != "game" or self.game is None:
            self.notice = f"not a command: {text}. /help lists them"
            return
        game = self.game
        if game.over:
            self.notice = "game over. /new starts another"
            return
        if game.pending_failure is not None:
            self.notice = "waiting on Gemma. /retry or /quit"
            return
        if game.board.turn != game.participant_color:
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
