"""Screen rendering. Everything returns lines of rich Text built from
view data; nothing here parses model output, adjudicates chess,
constructs prompts, or touches SQLite. The styled board walks the same
BoardGrid as the plain text contract, so color can never move a cell.

Layout is one screen at a time for a portrait phone terminal. The game
screen order is fixed: status line, board, last move and state, at
most two wrapped lines of commentary, then the input line the app
prints its prompt on."""

import textwrap
from dataclasses import dataclass

from rich.text import Text

from chess_tui.actions.replay import HistoryItem, ReplayCursor
from chess_tui.calculations.board_view import board_grid, board_lines
from chess_tui.calculations.stats import Record, participant_lost, participant_won
from chess_tui.ui.theme import Theme

COMMENT_LINES = 2


@dataclass(frozen=True)
class GameView:
    fen: str
    flipped: bool
    move_number: int
    player_label: str  # "ramon: White"
    gemma_label: str  # "Gemma: Black"
    last_move_uci: str | None
    last_move_label: str
    state_word: str
    state_tone: str  # "neutral" | "good" | "bad"
    comment: str | None
    notice: str | None
    failure_headline: str | None
    failure_detail: str | None
    game_over: bool


def clip(text: str, width: int) -> str:
    return text if len(text) <= width else text[: width - 3] + "..."


# Tall board (two rows per rank) is 18 board lines. In tall mode the
# blank separator lines go away, so a mid-game frame is 22 rows plus
# the input and suggestion rows: 24 total. Ramon's phone with the soft
# keyboard open is about 26 rows, which is why the old threshold of 27
# quietly never fired on the one device that mattered. A game-over or
# replay frame can run up to two rows over on a terminal of exactly
# 24; the status line scrolling off at checkmate is a fair trade for
# square squares. CHESS_TUI_TALL=always|never overrides the guess.
TALL_MIN_HEIGHT = 24


def use_tall(height: int, mode: str = "auto") -> bool:
    if mode == "always":
        return True
    if mode == "never":
        return False
    return height >= TALL_MIN_HEIGHT


def render_board(
    fen: str, last_move_uci: str | None, flipped: bool, theme: Theme, tall: bool = False
) -> list[Text]:
    grid = board_grid(fen, last_move_uci, flipped)
    plain = board_lines(grid)
    lines = [Text(plain[0], style=theme.faint)]
    for label, row in zip(grid.rank_labels, grid.rows, strict=True):
        line = Text()
        line.append(f" {label} ", style=theme.faint)
        pad = Text("   ")
        for cell in row:
            if cell.piece == ".":
                piece_style = theme.empty_square
            elif cell.piece.isupper():
                piece_style = theme.white_piece
            else:
                piece_style = theme.black_piece
            background = theme.square_background(
                cell.is_light, cell.is_last_from or cell.is_last_to
            )
            style = piece_style
            if background:
                style = f"{piece_style} on {background}" if piece_style else f"on {background}"
            line.append(f" {cell.piece}  ", style=style)
            pad.append("    ", style=f"on {background}" if background else "")
        line.append(f" {label}", style=theme.faint)
        lines.append(line)
        if tall:
            lines.append(pad)
    lines.append(Text(plain[-1], style=theme.faint))
    return lines


def game_screen(view: GameView, theme: Theme, width: int, tall: bool = False) -> list[Text]:
    """In tall mode the blank separators go: the fat board carries its
    own visual spacing and the saved rows are what let tall fit a
    phone with the keyboard open."""
    tone = {"good": theme.good, "bad": theme.bad}.get(view.state_tone, theme.soft)
    status = f"{view.player_label} | {view.gemma_label} | move {view.move_number}"
    lines = [Text(clip(status, width), style=theme.ink)]
    if not tall:
        lines.append(Text(""))
    lines.extend(render_board(view.fen, view.last_move_uci, view.flipped, theme, tall))
    if not tall:
        lines.append(Text(""))

    state_line = Text()
    state_line.append(clip(view.last_move_label, width), style=theme.ink)
    if view.state_word:
        state_line.append("  ")
        state_line.append(view.state_word, style=tone)
    lines.append(state_line)

    if view.notice:
        lines.append(Text(clip(view.notice, width), style=theme.bad))
    if view.failure_headline:
        lines.append(Text(clip(view.failure_headline, width), style=theme.bad))
        if view.failure_detail:
            lines.append(Text(clip(view.failure_detail, width), style=theme.faint))
    elif view.comment:
        for wrapped in _wrap_comment(view.comment, width):
            lines.append(Text(wrapped, style=theme.soft))

    if view.game_over:
        lines.append(Text(""))
        lines.append(Text(clip("/new  /history  /replay  /help  /quit", width), style=theme.faint))
    return lines


def _wrap_comment(comment: str, width: int) -> list[str]:
    return textwrap.wrap(
        f"gemma: {comment}",
        width=max(20, width),
        max_lines=COMMENT_LINES,
        placeholder=" ...",
    )


def home_screen(
    record: Record,
    model: str,
    player_name: str,
    theme: Theme,
    width: int,
    game_in_progress: bool = False,
) -> list[Text]:
    lines = [
        Text("chess tui", style=f"bold {theme.ink}" if theme.ink else ""),
        Text(clip(f"{player_name} vs {model}", width), style=theme.faint),
        Text(""),
    ]
    record_line = Text()
    record_line.append("record  ", style=theme.faint)
    record_line.append(f"W {record.wins}  ", style=theme.good)
    record_line.append(f"L {record.losses}  ", style=theme.bad)
    record_line.append(f"D {record.draws}", style=theme.soft)
    lines.append(record_line)
    captures = Text()
    captures.append("captures in wins  ", style=theme.faint)
    captures.append(str(record.captures_in_wins), style=theme.ink)
    lines.append(captures)
    lines.append(Text(""))
    if game_in_progress:
        lines.append(Text("game in progress. /back returns to it", style=theme.accent))
    lines.append(Text("/new  /history  /replay  /help  /quit", style=theme.faint))
    return lines


def history_screen(items: list[HistoryItem], theme: Theme, width: int) -> list[Text]:
    lines = [Text("history", style=f"bold {theme.ink}" if theme.ink else ""), Text("")]
    if not items:
        lines.append(Text("no games yet", style=theme.soft))
    for number, item in enumerate(items, start=1):
        when = item.started_at[:16].replace("T", " ")
        outcome = item.result or "unfinished"
        if item.termination:
            outcome = f"{outcome} {item.termination}"
        as_color = item.participant_color[:1].upper()
        row = f"{number:>2}  {when}  {as_color}  {outcome}  {item.move_count} moves"
        if participant_won(item.result, item.participant_color):
            tone = theme.good
        elif participant_lost(item.result, item.participant_color):
            tone = theme.bad
        else:
            tone = theme.soft
        lines.append(Text(clip(row, width), style=tone))
    lines.append(Text(""))
    lines.append(Text("/replay <number>  /new  /back", style=theme.faint))
    return lines


def replay_screen(
    cursor: ReplayCursor, flipped: bool, theme: Theme, width: int, tall: bool = False
) -> list[Text]:
    when = cursor.started_at[:16].replace("T", " ")
    outcome = cursor.result or "unfinished"
    header = f"replay  {when}  {outcome}  as {cursor.participant_color}"
    lines = [Text(clip(header, width), style=theme.ink)]
    if not tall:
        lines.append(Text(""))
    current = cursor.current
    lines.extend(render_board(cursor.fen, current.uci if current else None, flipped, theme, tall))
    if not tall:
        lines.append(Text(""))
    if current is None:
        position = "start"
    else:
        label = move_label(current.ply, current.san)
        position = f"ply {cursor.index}/{len(cursor.plies)}  {label}"
    lines.append(Text(clip(position, width), style=theme.ink))
    if current is not None and current.comment:
        for wrapped in _wrap_comment(current.comment, width):
            lines.append(Text(wrapped, style=theme.soft))
    if not tall:
        lines.append(Text(""))
    lines.append(Text(clip("/next  /prev  /flip  /back. enter is next", width), style=theme.faint))
    return lines


def help_screen(theme: Theme, width: int) -> list[Text]:
    rows = [
        ("moves", "type e2e4 or Nf3. promotion e7e8q or e8=Q"),
        ("/new", "start a game. a coin toss picks your color"),
        ("/back", "return to the game or previous screen"),
        ("/history", "past games, newest first"),
        ("/replay", "step through a stored game"),
        ("/retry", "repeat a failed model turn"),
        ("/flip", "turn the board around"),
        ("/quit", "leave the screen. at home, exit"),
    ]
    lines = [Text("help", style=f"bold {theme.ink}" if theme.ink else ""), Text("")]
    for name, description in rows:
        row = Text()
        row.append(f"{name:<10}", style=theme.accent)
        row.append(clip(description, width - 10), style=theme.soft)
        lines.append(row)
    lines.append(Text(""))
    lines.append(Text(clip("bare words work too. NO_COLOR drops color", width), style=theme.faint))
    return lines


def move_label(ply: int, san: str) -> str:
    number = (ply + 1) // 2
    return f"{number}. {san}" if ply % 2 == 1 else f"{number}...{san}"
