"""Command parsing: slash commands are canonical, bare keywords still
work, unknown slash commands are their own thing, and everything else
is candidate move text."""

from chess_tui.calculations.commands import Command, MoveText, UnknownCommand, parse_input


def test_slash_commands_parse():
    for word in [
        "new",
        "history",
        "replay",
        "retry",
        "flip",
        "help",
        "quit",
        "back",
        "next",
        "prev",
    ]:
        assert parse_input(f"/{word}") == Command(word)


def test_bare_keywords_still_work():
    for word in ["new", "history", "retry", "flip", "help", "quit", "back"]:
        assert parse_input(word) == Command(word)


def test_quit_and_back_aliases():
    assert parse_input("q") == Command("quit")
    assert parse_input("exit") == Command("quit")
    assert parse_input("b") == Command("back")
    assert parse_input("resume") == Command("back")
    assert parse_input("n") == Command("next")
    assert parse_input("p") == Command("prev")


def test_replay_with_number():
    assert parse_input("/replay 3") == Command("replay", 3)
    assert parse_input("replay 3") == Command("replay", 3)


def test_bare_number_is_replay_selection():
    assert parse_input("2") == Command("replay", 2)


def test_blank_line():
    assert parse_input("   ") == Command("blank")


def test_case_insensitive_commands():
    assert parse_input("/New") == Command("new")
    assert parse_input("QUIT") == Command("quit")


def test_unknown_slash_command_is_not_a_move():
    parsed = parse_input("/teleport")
    assert parsed == UnknownCommand("/teleport")


def test_moves_pass_through():
    assert parse_input("e2e4") == MoveText("e2e4")
    assert parse_input("Nf3") == MoveText("Nf3")
    assert parse_input("e8=Q") == MoveText("e8=Q")
