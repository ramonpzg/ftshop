"""The input line: suggestion matching, the editor state machine fed
character by character, and one real pty round trip for the raw-mode
wrapper."""

import os
import select
import subprocess
import sys
import time

import pytest

from chess_tui.calculations.commands import SLASH_COMMANDS, command_suggestions
from chess_tui.ui.input_line import LineEditor


def test_suggestions_match_prefixes():
    assert command_suggestions("/") == SLASH_COMMANDS
    assert command_suggestions("/h") == ["/history", "/help"]  # declared order
    assert command_suggestions("/re") == ["/replay", "/retry"]
    assert command_suggestions("/quit") == ["/quit"]
    assert command_suggestions("/Q") == ["/quit"]


def test_no_suggestions_for_moves_arguments_or_unknowns():
    assert command_suggestions("e2e4") == []
    assert command_suggestions("") == []
    assert command_suggestions("/replay 1") == []
    assert command_suggestions("/xyz") == []


def _type(editor: LineEditor, text: str) -> str | None:
    result = None
    for char in text:
        result = editor.feed(char)
    return result


def test_editor_collects_and_submits():
    editor = LineEditor(command_suggestions)
    assert _type(editor, "e2e4") is None
    assert editor.text == "e2e4"
    assert editor.feed("\r") == "e2e4"


def test_editor_backspace():
    editor = LineEditor(command_suggestions)
    _type(editor, "/neq")
    editor.feed("\x7f")
    assert editor.text == "/ne"
    assert editor.suggestions() == ["/new", "/next"]


def test_editor_tab_completes_common_prefix_then_sole_match():
    editor = LineEditor(command_suggestions)
    _type(editor, "/re")
    editor.feed("\t")
    assert editor.text == "/re"  # /replay and /retry share nothing more
    _type(editor, "t")
    editor.feed("\t")
    assert editor.text == "/retry "  # sole match completes with a space
    assert editor.feed("\r") == "/retry "


def test_editor_tab_extends_partial_common_prefix():
    editor = LineEditor(command_suggestions)
    _type(editor, "/h")
    editor.feed("\t")
    assert editor.text == "/h"  # /help and /history diverge immediately after /h
    _type(editor, "i")
    editor.feed("\t")
    assert editor.text == "/history "


def test_editor_swallows_arrow_keys_csi_and_ss3():
    editor = LineEditor(command_suggestions)
    _type(editor, "/ne")
    for sequence in ("\x1b[A", "\x1bOB", "\x1b[1;5C"):
        for char in sequence:
            editor.feed(char)
    assert editor.text == "/ne"


def test_editor_ctrl_d_on_empty_raises_eof():
    editor = LineEditor(command_suggestions)
    with pytest.raises(EOFError):
        editor.feed("\x04")
    editor2 = LineEditor(command_suggestions)
    _type(editor2, "/n")
    editor2.feed("\x04")  # mid-line Ctrl+D is ignored
    assert editor2.text == "/n"


def test_editor_enter_on_empty_line_is_blank():
    editor = LineEditor(command_suggestions)
    assert editor.feed("\n") == ""


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="pty smoke is linux-only")
def test_read_line_over_a_real_pty():
    """stdin AND stdout are the pty, so the raw-mode path runs for
    real: typed prefix, tab completion, enter, suggestion redraws."""
    import pty

    master, slave = pty.openpty()
    child = subprocess.Popen(
        [
            sys.executable,
            "-c",
            "from chess_tui.ui.input_line import read_line\n"
            "from chess_tui.calculations.commands import command_suggestions\n"
            "line = read_line('> ', command_suggestions)\n"
            "print('GOT:' + line)",
        ],
        stdin=slave,
        stdout=slave,
        stderr=subprocess.PIPE,
    )
    os.close(slave)
    collected = b""
    typed = False
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        readable, _, _ = select.select([master], [], [], 0.25)
        if master in readable:
            try:
                chunk = os.read(master, 1024)
            except OSError:  # EIO once the child exits and the slave closes
                break
            if not chunk:
                break
            collected += chunk
        elif child.poll() is not None:
            break
        if not typed and b"> " in collected:
            os.write(master, b"/ret\t\r")  # type only once the prompt is up
            typed = True
        if b"GOT:" in collected and child.poll() is not None:
            break
    os.close(master)
    try:
        _, err = child.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        child.kill()
        _, err = child.communicate()
    assert child.returncode == 0, err.decode()
    assert b"GOT:/retry" in collected
