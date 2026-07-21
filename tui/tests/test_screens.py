"""Rendering at the target phone widths. The styled board must occupy
exactly the same cells as the plain contract, comments must wrap to at
most two lines, and the White/Black case distinction must survive with
color stripped."""

import chess
import pytest
from rich.console import Console

from chess_tui.actions.replay import ReplayCursor, ReplayPly
from chess_tui.calculations.board_view import board_grid, board_lines
from chess_tui.calculations.stats import Record
from chess_tui.ui.screens import (
    GameView,
    game_screen,
    help_screen,
    history_screen,
    home_screen,
    move_label,
    render_board,
    replay_screen,
)
from chess_tui.ui.theme import CHALK, PLAIN

TARGET_WIDTHS = [40, 48, 60, 80]


def _export(lines, width: int) -> list[str]:
    console = Console(record=True, width=width, force_terminal=True)
    for line in lines:
        console.print(line, no_wrap=True, overflow="crop")
    return console.export_text().splitlines()


def _view(**overrides) -> GameView:
    board = chess.Board()
    board.push_uci("e2e4")
    board.push_uci("e7e5")
    defaults = dict(
        fen=board.fen(),
        flipped=False,
        move_number=2,
        last_move_uci="e7e5",
        last_move_label="1...e5",
        state_word="",
        state_tone="neutral",
        comment="Symmetry. The opening theory writes itself, sadly.",
        notice=None,
        failure_headline=None,
        failure_detail=None,
        game_over=False,
    )
    defaults.update(overrides)
    return GameView(**defaults)


@pytest.mark.parametrize("width", TARGET_WIDTHS)
@pytest.mark.parametrize("theme", [CHALK, PLAIN], ids=["chalk", "plain"])
def test_game_screen_board_alignment_at_every_target_width(width, theme):
    view = _view()
    exported = _export(game_screen(view, theme, width), width)
    plain = board_lines(board_grid(view.fen, view.last_move_uci))
    start = exported.index(plain[0])
    assert exported[start : start + len(plain)] == plain
    assert all(len(line) <= width for line in exported)


@pytest.mark.parametrize("width", TARGET_WIDTHS)
def test_comment_wraps_to_at_most_two_lines(width):
    from chess_tui.ui.screens import _wrap_comment

    long_comment = (
        "A comment that runs long enough to need wrapping on a narrow "
        "portrait phone terminal, which is the whole point here."
    )
    wrapped = _wrap_comment(long_comment, width)
    assert 1 <= len(wrapped) <= 2
    assert wrapped[0].startswith("gemma:")
    assert all(len(line) <= width for line in wrapped)
    if len(f"gemma: {long_comment}") > width * 2:
        assert wrapped[-1].endswith("...")

    exported = _export(game_screen(_view(comment=long_comment), PLAIN, width), width)
    assert any(line.startswith("gemma:") for line in exported)


def test_status_line_matches_the_spec():
    exported = _export(game_screen(_view(), PLAIN, 40), 40)
    assert exported[0] == "You: White | Gemma: Black | move 2"


def test_white_black_distinction_survives_without_color():
    exported = "\n".join(_export(game_screen(_view(), PLAIN, 40), 40))
    assert "R N B Q K B" in exported  # White, uppercase
    assert "r n b q k b n r" in exported  # Black, lowercase


def test_check_and_failure_states_are_visible():
    view = _view(
        state_word="check",
        state_tone="bad",
        failure_headline="Gemma did not return a legal move. retry or quit",
        failure_detail='move "a1a1" is not in LEGAL_MOVES',
    )
    exported = "\n".join(_export(game_screen(view, CHALK, 48), 48))
    assert "check" in exported
    assert "Gemma did not return a legal move. retry or quit" in exported
    assert "a1a1" in exported


def test_game_over_screen_offers_next_commands():
    view = _view(state_word="checkmate. white won", state_tone="good", game_over=True)
    exported = "\n".join(_export(game_screen(view, PLAIN, 40), 40))
    assert "checkmate. white won" in exported
    assert "new  history  replay  help  quit" in exported


@pytest.mark.parametrize("width", TARGET_WIDTHS)
def test_home_history_replay_help_fit_the_width(width):
    record = Record(wins=2, losses=1, draws=0, completed=3, captures_in_wins=9)
    lines = home_screen(record, "gemma-4-2b-local", CHALK, width)
    plies = [
        ReplayPly(1, "participant", "e2e4", "e4", chess.Board().fen(), None),
    ]
    cursor = ReplayCursor(
        game_id="g",
        started_at="2026-07-21T10:00:00+00:00",
        result="1-0",
        termination="checkmate",
        plies=plies,
        index=1,
    )
    from chess_tui.actions.replay import HistoryItem

    items = [
        HistoryItem("g", "2026-07-21T10:00:00+00:00", "1-0", "checkmate", 9),
        HistoryItem("h", "2026-07-21T09:00:00+00:00", None, None, 4),
    ]
    for screen_lines in [
        lines,
        history_screen(items, CHALK, width),
        replay_screen(cursor, False, CHALK, width),
        help_screen(CHALK, width),
    ]:
        exported = _export(screen_lines, width)
        assert all(len(line) <= width for line in exported)


def test_home_screen_shows_record_and_objective():
    record = Record(wins=2, losses=1, draws=0, completed=3, captures_in_wins=9)
    exported = "\n".join(_export(home_screen(record, "gemma-4-2b-local", PLAIN, 40), 40))
    assert "W 2" in exported
    assert "L 1" in exported
    assert "captures in wins" in exported
    assert "9" in exported


def test_history_screen_labels_unfinished_games():
    from chess_tui.actions.replay import HistoryItem

    items = [HistoryItem("h", "2026-07-21T09:00:00+00:00", None, None, 4)]
    exported = "\n".join(_export(history_screen(items, PLAIN, 48), 48))
    assert "unfinished" in exported
    assert "4 moves" in exported


def test_replay_screen_shows_ply_position_and_comment():
    board = chess.Board()
    board.push_uci("e2e4")
    fen_after_e4 = board.fen()
    board.push_uci("e7e5")
    plies = [
        ReplayPly(1, "participant", "e2e4", "e4", fen_after_e4, None),
        ReplayPly(2, "model", "e7e5", "e5", board.fen(), "Symmetry. Bold."),
    ]
    cursor = ReplayCursor(
        game_id="g",
        started_at="2026-07-21T10:00:00+00:00",
        result=None,
        termination=None,
        plies=plies,
        index=2,
    )
    exported = "\n".join(_export(replay_screen(cursor, False, PLAIN, 48), 48))
    assert "ply 2/2" in exported
    assert "1...e5" in exported
    assert "gemma: Symmetry. Bold." in exported


def test_move_label_numbering():
    assert move_label(1, "e4") == "1. e4"
    assert move_label(2, "e5") == "1...e5"
    assert move_label(15, "Qh5") == "8. Qh5"


def test_render_board_flipped_matches_plain_flipped():
    fen = chess.STARTING_FEN
    exported = _export(render_board(fen, None, True, CHALK), 40)
    assert exported == board_lines(board_grid(fen, None, True))
