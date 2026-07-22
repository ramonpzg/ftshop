"""The input line: a small raw-mode reader that shows live command
suggestions under the prompt while a slash command is being typed, and
completes it on tab. On anything that is not an interactive terminal
it falls back to plain input(), so pipes, tests, and the smoke command
behave exactly as before.

The editor logic is a pure state machine (feed bytes, get back a line
or nothing) so it tests without a terminal; the tty wrapper only owns
termios and drawing. Arrow keys and other escape sequences are
swallowed rather than interpreted: phone keyboards type characters,
and the phase prompt's no-cursor-choreography rule still stands."""

import codecs
import os
import sys
from collections.abc import Callable

_BACKSPACE = ("\x7f", "\x08")
_ENTER = ("\r", "\n")
_CTRL_D = "\x04"
_ESC = "\x1b"

SuggestFn = Callable[[str], list[str]]


class LineEditor:
    """Feed decoded characters; returns the finished line on enter.
    Raises EOFError on Ctrl+D with an empty buffer (matching input());
    Ctrl+C never reaches us because cbreak keeps ISIG on."""

    def __init__(self, suggest: SuggestFn) -> None:
        self._suggest = suggest
        self._chars: list[str] = []
        self._in_escape = False
        self._escape_intro = False

    @property
    def text(self) -> str:
        return "".join(self._chars)

    def suggestions(self) -> list[str]:
        return self._suggest(self.text)

    def feed(self, char: str) -> str | None:
        if self._in_escape:
            if self._escape_intro:
                self._escape_intro = False
                if char in "[O":
                    return None  # CSI/SS3: keep consuming to the final byte
                self._in_escape = False  # ESC plus one char (alt-chord); swallow
                return None
            # CSI/SS3 sequences end on an alphabetic final byte or ~.
            if char.isalpha() or char == "~":
                self._in_escape = False
            return None
        if char == _ESC:
            self._in_escape = True
            self._escape_intro = True
            return None
        if char in _ENTER:
            return self.text
        if char in _BACKSPACE:
            if self._chars:
                self._chars.pop()
            return None
        if char == _CTRL_D:
            if not self._chars:
                raise EOFError
            return None
        if char == "\t":
            self._complete()
            return None
        if char.isprintable():
            self._chars.append(char)
        return None

    def _complete(self) -> None:
        matches = self.suggestions()
        if not matches:
            return
        common = os.path.commonprefix(matches)
        if len(common) > len(self.text):
            self._chars = list(common)
            if len(matches) == 1:
                self._chars.append(" ")


def read_line(prompt: str, suggest: SuggestFn, no_color: bool = False) -> str:
    """Interactive line read with a live suggestion row. Non-tty
    stdin or stdout falls back to builtins input()."""
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        return input(prompt)
    editor = LineEditor(suggest)
    fd = sys.stdin.fileno()
    import termios
    import tty

    decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
    old_attrs = termios.tcgetattr(fd)
    out = sys.stdout
    try:
        # TCSADRAIN, not the TCSAFLUSH default: flushing would discard
        # anything typed before the prompt appeared.
        tty.setcbreak(fd, termios.TCSADRAIN)
        _draw(out, prompt, editor, no_color)
        while True:
            byte = os.read(fd, 1)
            if not byte:
                raise EOFError
            for char in decoder.decode(byte):
                line = editor.feed(char)
                if line is not None:
                    _clear_suggestion_row(out)
                    out.write("\r\n")
                    out.flush()
                    return line
            _draw(out, prompt, editor, no_color)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_attrs)


def _draw(out, prompt: str, editor: LineEditor, no_color: bool) -> None:
    suggestions = "  ".join(editor.suggestions())
    out.write("\x1b7")  # save cursor
    out.write("\n\r\x1b[K")  # suggestion row below the input line
    if suggestions:
        if no_color:
            out.write(suggestions)
        else:
            out.write(f"\x1b[2m{suggestions}\x1b[0m")
    out.write("\x1b8")  # restore cursor
    out.write(f"\r\x1b[K{prompt}{editor.text}")
    out.flush()


def _clear_suggestion_row(out) -> None:
    out.write("\x1b7\n\r\x1b[K\x1b8")
