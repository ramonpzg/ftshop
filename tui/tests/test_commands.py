"""Command parsing: known keywords become commands, everything else is
candidate move text."""

from chess_tui.calculations.commands import Command, MoveText, parse_input


def test_known_commands_parse():
    for word in ["new", "history", "replay", "retry", "flip", "help", "quit", "next", "prev"]:
        parsed = parse_input(word)
        assert parsed == Command(word)


def test_quit_aliases():
    assert parse_input("q") == Command("quit")
    assert parse_input("exit") == Command("quit")


def test_replay_with_number():
    assert parse_input("replay 3") == Command("replay", 3)


def test_bare_number_is_replay_selection():
    assert parse_input("2") == Command("replay", 2)


def test_blank_line():
    assert parse_input("   ") == Command("blank")


def test_case_insensitive_commands():
    assert parse_input("New") == Command("new")
    assert parse_input("QUIT") == Command("quit")


def test_moves_pass_through():
    assert parse_input("e2e4") == MoveText("e2e4")
    assert parse_input("Nf3") == MoveText("Nf3")
    assert parse_input("e8=Q") == MoveText("e8=Q")
