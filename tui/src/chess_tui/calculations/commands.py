"""Pure command-line parsing. Commands are slash-prefixed (/new,
/help) so they can never collide with a move; the bare words still
work because no chess move spells them. Anything else is candidate
move text for the move parser to judge."""

from dataclasses import dataclass
from typing import Literal

CommandKind = Literal[
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
    "blank",
]

_ALIASES: dict[str, CommandKind] = {
    "new": "new",
    "history": "history",
    "replay": "replay",
    "retry": "retry",
    "flip": "flip",
    "help": "help",
    "quit": "quit",
    "q": "quit",
    "exit": "quit",
    "back": "back",
    "b": "back",
    "resume": "back",
    "next": "next",
    "n": "next",
    "prev": "prev",
    "p": "prev",
}


# Canonical spellings, in the order the suggestion line shows them.
SLASH_COMMANDS = [
    "/new",
    "/back",
    "/history",
    "/replay",
    "/retry",
    "/flip",
    "/help",
    "/quit",
    "/next",
    "/prev",
]


def command_suggestions(typed: str) -> list[str]:
    """Live matches for a partially typed slash command. Only the
    command token suggests; once an argument starts, silence."""
    if not typed.startswith("/") or " " in typed:
        return []
    prefix = typed.lower()
    return [command for command in SLASH_COMMANDS if command.startswith(prefix)]


@dataclass(frozen=True)
class Command:
    kind: CommandKind
    arg: int | None = None


@dataclass(frozen=True)
class UnknownCommand:
    text: str


@dataclass(frozen=True)
class MoveText:
    text: str


def parse_input(line: str) -> Command | UnknownCommand | MoveText:
    tokens = line.strip().split()
    if not tokens:
        return Command("blank")
    head = tokens[0].lower()
    slashed = head.startswith("/")
    if slashed:
        head = head[1:]
    if head in _ALIASES:
        kind = _ALIASES[head]
        arg = None
        if kind == "replay" and len(tokens) > 1 and tokens[1].isdigit():
            arg = int(tokens[1])
        return Command(kind, arg)
    if slashed:
        return UnknownCommand(tokens[0])
    if head.isdigit() and len(tokens) == 1:
        return Command("replay", int(head))
    return MoveText(line.strip())
