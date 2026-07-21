"""Rendering at the target phone widths. The styled board must occupy
exactly the same cells as the plain contract, comments must wrap to at
most two lines, and the White/Black case distinction must survive with
color stripped."""

import chess
import pytest
from rich.console import Console

from chess_tui.actions.replay import HistoryItem, ReplayCursor, ReplayPly
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
        player_label="ramon: White",
        gemma_label="Gemma: Black",
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


def test_status_line_carries_names_and_colors():
    exported = _export(game_screen(_view(), PLAIN, 48), 48)
    assert exported[0] == "ramon: White | Gemma: Black | move 2"
    swapped = _view(player_label="ramon: Black", gemma_label="Gemma: White")
    exported = _export(game_screen(swapped, PLAIN, 48), 48)
    assert exported[0] == "ramon: Black | Gemma: White | move 2"


def test_white_black_distinction_survives_without_color():
    exported = "\n".join(_export(game_screen(_view(), PLAIN, 40), 40))
    assert "R   N   B   Q   K   B" in exported  # White, uppercase
    assert "r   n   b   q   k   b   n   r" in exported  # Black, lowercase


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
    view = _view(state_word="checkmate. ramon won", state_tone="good", game_over=True)
    exported = "\n".join(_export(game_screen(view, PLAIN, 40), 40))
    assert "checkmate. ramon won" in exported
    assert "/new  /history  /replay  /help  /quit" in exported


def _history_items():
    return [
        HistoryItem("g", "2026-07-21T10:00:00+00:00", "1-0", "checkmate", 9, "white"),
        HistoryItem("h", "2026-07-21T09:00:00+00:00", "1-0", "checkmate", 7, "black"),
        HistoryItem("i", "2026-07-21T08:00:00+00:00", None, None, 4, "black"),
    ]


def _cursor(index=1):
    plies = [ReplayPly(1, "participant", "e2e4", "e4", chess.Board().fen(), None)]
    return ReplayCursor(
        game_id="g",
        started_at="2026-07-21T10:00:00+00:00",
        result="1-0",
        termination="checkmate",
        participant_color="black",
        plies=plies,
        index=index,
    )


@pytest.mark.parametrize("width", TARGET_WIDTHS)
def test_home_history_replay_help_fit_the_width(width):
    record = Record(wins=2, losses=1, draws=0, completed=3, captures_in_wins=9)
    screens = [
        home_screen(record, "gemma-4-2b-local", "ramon", CHALK, width, game_in_progress=True),
        history_screen(_history_items(), CHALK, width),
        replay_screen(_cursor(), False, CHALK, width),
        help_screen(CHALK, width),
    ]
    for screen_lines in screens:
        exported = _export(screen_lines, width)
        assert all(len(line) <= width for line in exported)


def test_home_screen_shows_name_record_objective_and_resume_hint():
    record = Record(wins=2, losses=1, draws=0, completed=3, captures_in_wins=9)
    exported = "\n".join(
        _export(
            home_screen(record, "gemma-4-2b-local", "ramon", PLAIN, 48, game_in_progress=True), 48
        )
    )
    assert "ramon vs gemma-4-2b-local" in exported
    assert "W 2" in exported
    assert "captures in wins" in exported
    assert "game in progress. /back returns to it" in exported

    without = "\n".join(_export(home_screen(record, "gemma-4-2b-local", "ramon", PLAIN, 48), 48))
    assert "game in progress" not in without


def test_history_screen_shows_color_and_win_tone_by_color():
    lines = history_screen(_history_items(), CHALK, 60)
    body = "\n".join(line.plain for line in lines)
    assert "W  1-0 checkmate" in body  # won as white
    assert "B  1-0 checkmate" in body  # same result string, lost as black
    assert "unfinished" in body
    win_row = next(line for line in lines if line.plain.startswith(" 1  "))
    loss_row = next(line for line in lines if line.plain.startswith(" 2  "))
    assert win_row.style == CHALK.good
    assert loss_row.style == CHALK.bad


def test_replay_screen_shows_ply_color_and_comment():
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
        participant_color="white",
        plies=plies,
        index=2,
    )
    exported = "\n".join(_export(replay_screen(cursor, False, PLAIN, 48), 48))
    assert "as white" in exported
    assert "ply 2/2" in exported
    assert "1...e5" in exported
    assert "gemma: Symmetry. Bold." in exported


def test_help_screen_lists_slash_commands():
    exported = "\n".join(_export(help_screen(PLAIN, 48), 48))
    assert "/back" in exported
    assert "/retry" in exported
    assert "coin toss" in exported
    assert "bare words work too" in exported


def test_move_label_numbering():
    assert move_label(1, "e4") == "1. e4"
    assert move_label(2, "e5") == "1...e5"
    assert move_label(15, "Qh5") == "8. Qh5"


def test_render_board_flipped_matches_plain_flipped():
    fen = chess.STARTING_FEN
    exported = _export(render_board(fen, None, True, CHALK), 40)
    assert exported == board_lines(board_grid(fen, None, True))


def test_tall_board_at_a_phone_height_keeps_alignment():
    view = _view()
    lines = game_screen(view, CHALK, 60, height=28)
    exported = _export(lines, 60)
    plain = board_lines(board_grid(view.fen, view.last_move_uci), tall=True)
    start = exported.index(plain[0])
    board_block = exported[start : start + len(plain)]
    # Styled filler rows carry backgrounds but no text; compare after
    # stripping, which is exactly what the plain contract promises.
    assert [line.rstrip() for line in board_block] == plain
    assert len(plain) == 18


def test_short_terminals_keep_the_single_height_board():
    view = _view()
    exported = _export(game_screen(view, CHALK, 60, height=24), 60)
    plain = board_lines(board_grid(view.fen, view.last_move_uci), tall=False)
    start = exported.index(plain[0])
    assert exported[start : start + len(plain)] == plain
