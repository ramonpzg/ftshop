"""The whole loop, driven end to end: scripted keyboard input, a
scripted transport, a real temp database, a recording console, a
seeded coin. No mouse, no chords, no mocking above the transport."""

import random

import httpx
import pytest
from conftest import fresh_connection, move_reply, scripted_client
from rich.console import Console

from chess_tui.data.config import Config
from chess_tui.ui.app import App

# random.Random(1).random() < 0.5 -> White; random.Random(0) -> Black.
WHITE_SEED = 1
BLACK_SEED = 0


class Keyboard:
    def __init__(self, lines):
        self.lines = list(lines)

    def __call__(self) -> str:
        if not self.lines:
            raise EOFError
        return self.lines.pop(0)


def run_app(config, conn, script, keys, width=48, seed=WHITE_SEED):
    client, scripted = scripted_client(config, script)
    console = Console(record=True, width=width, force_terminal=False, no_color=True)
    app = App(
        config, conn, client, console=console, input_fn=Keyboard(keys), rng=random.Random(seed)
    )
    app.run()
    client.close()
    return console.export_text(), scripted, app


def test_seed_expectations_hold():
    assert random.Random(WHITE_SEED).random() < 0.5
    assert random.Random(BLACK_SEED).random() >= 0.5


def test_new_game_move_reply_and_quit(config, conn, db_path):
    output, scripted, app = run_app(
        config,
        conn,
        [move_reply("e7e5", "Symmetry. How original.")],
        ["/new", "e2e4", "/quit", "/quit"],
    )
    assert "tester: White | Gemma: Black" in output
    assert "Gemma is choosing..." in output
    assert "1...e5" in output
    assert "gemma: Symmetry. How original." in output

    other = fresh_connection(db_path)
    plies = other.execute("SELECT uci FROM plies ORDER BY ply").fetchall()
    assert [row["uci"] for row in plies] == ["e2e4", "e7e5"]
    other.close()


def test_coin_toss_black_gemma_opens_and_board_is_flipped(config, conn):
    output, _, app = run_app(
        config,
        conn,
        [move_reply("e2e4", "I will take the center, thanks.")],
        ["/new", "/quit", "/quit"],
        seed=BLACK_SEED,
    )
    assert "tester: Black | Gemma: White" in output
    assert "    h  g  f  e  d  c  b  a" in output  # oriented to the participant
    assert "1. e4" in output
    assert "gemma: I will take the center, thanks." in output


def test_help_from_game_returns_with_back(config, conn):
    output, _, app = run_app(
        config,
        conn,
        [move_reply("e7e5", "Fine.")],
        ["/new", "e2e4", "/help", "/back", "/quit", "/quit"],
    )
    assert "/back" in output
    assert app.game is not None
    # after /back the game frame rendered again with the reply on board
    assert output.count("1...e5") >= 2


def test_quit_from_game_keeps_it_resumable_from_home(config, conn):
    output, _, app = run_app(
        config,
        conn,
        [move_reply("e7e5", "Fine.")],
        ["/new", "e2e4", "/quit", "/back", "/quit", "/quit"],
    )
    assert "game in progress. /back returns to it" in output
    assert app.game is not None
    assert output.count("tester: White") >= 2  # game screen shown again after /back


def test_illegal_typed_move_shows_notice_and_changes_nothing(config, conn, db_path):
    output, scripted, _ = run_app(config, conn, [], ["/new", "e2e5", "/quit", "/quit"])
    assert "illegal move: e2e5" in output
    assert scripted.requests == []
    other = fresh_connection(db_path)
    assert other.execute("SELECT COUNT(*) AS n FROM plies").fetchone()["n"] == 0
    other.close()


def test_unknown_slash_command_gets_a_notice(config, conn):
    output, _, _ = run_app(config, conn, [], ["/teleport", "/quit"])
    assert "unknown command /teleport. /help lists them" in output


def test_server_down_shows_retry_state_and_retry_recovers(config, conn):
    output, _, app = run_app(
        config,
        conn,
        [httpx.ConnectError("refused"), move_reply("e7e5", "Persistent, are we.")],
        ["/new", "e2e4", "/retry", "/quit", "/quit"],
    )
    assert "server unreachable. retry or quit" in output
    assert "1...e5" in output


def test_two_invalid_replies_then_retry_keeps_the_recording_recoverable(config, conn):
    output, _, _ = run_app(
        config,
        conn,
        ["nonsense", "still nonsense", move_reply("g8f6", "Better.")],
        ["/new", "d2d4", "/retry", "/quit", "/quit"],
    )
    assert "Gemma did not return a legal move. retry or quit" in output
    assert "1...Nf6" in output


def test_history_and_replay_flow(config, conn):
    output, _, _ = run_app(
        config,
        conn,
        [move_reply("e7e5", "Fine.")],
        [
            "/new",
            "e2e4",
            "/quit",
            "/history",
            "1",
            "/next",
            "",
            "/prev",
            "/back",
            "/back",
            "/quit",
            "/quit",
        ],
    )
    assert "history" in output
    assert "unfinished" in output
    assert "as white" in output
    assert "ply 1/2" in output
    assert "ply 2/2" in output


def test_flip_command_flips_the_board(config, conn):
    output, _, _ = run_app(config, conn, [], ["/new", "/flip", "/quit", "/quit"])
    assert "    h  g  f  e  d  c  b  a" in output


def test_move_when_no_game_is_a_notice_not_a_crash(config, conn):
    output, _, _ = run_app(config, conn, [], ["e2e4", "/quit"])
    assert "not a command: e2e4" in output


def test_retry_with_nothing_pending_is_a_notice(config, conn):
    output, _, _ = run_app(config, conn, [], ["/new", "/retry", "/quit", "/quit"])
    assert "nothing to retry" in output


def test_replay_with_no_games_says_so(config, conn):
    output, _, _ = run_app(config, conn, [], ["/replay", "/quit"])
    assert "no games yet" in output


def test_checkmate_shows_named_result_and_record(config, conn):
    replies = [move_reply("e7e5"), move_reply("b8c6"), move_reply("g8f6")]
    keys = ["/new", "e2e4", "d1h5", "f1c4", "h5f7", "/quit", "/quit"]
    output, _, _ = run_app(config, conn, replies, keys)
    assert "checkmate. tester won" in output
    assert "W 1" in output
    assert "captures in wins  1" in output


def test_name_is_asked_once_persisted_and_claims_old_games(db_path, conn):
    nameless = Config(db_path=db_path, no_color=True)
    output, _, app = run_app(nameless, conn, [], ["ramon", "/quit"])
    assert "your name?" in output
    assert app.player_name == "ramon"
    assert "ramon vs" in output

    # Second run: no question, name loaded from settings.
    conn2 = fresh_connection(db_path)
    output2, _, app2 = run_app(nameless, conn2, [], ["/quit"])
    assert "your name?" not in output2
    assert app2.player_name == "ramon"
    conn2.close()


def test_blank_name_defaults(db_path, conn):
    nameless = Config(db_path=db_path, no_color=True)
    output, _, app = run_app(nameless, conn, [], ["   ", "/quit"])
    assert app.player_name == "player"


@pytest.mark.parametrize("width", [40, 48, 60, 80])
def test_no_line_ever_exceeds_the_terminal_width(config, conn, width):
    output, _, _ = run_app(
        config,
        conn,
        [move_reply("e7e5", "A comment long enough to wrap on the narrowest phone screen.")],
        ["/new", "e2e4", "/history", "/quit", "/quit", "/quit"],
        width=width,
    )
    assert all(len(line) <= width for line in output.splitlines())
