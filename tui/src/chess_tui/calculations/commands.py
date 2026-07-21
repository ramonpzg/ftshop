"""Pure command-line parsing. Anything that is not a known command is
returned as candidate move text for the move parser to judge."""

from dataclasses import dataclass
from typing import Literal

CommandKind = Literal[
    "new", "history", "replay", "retry", "flip", "help", "quit", "next", "prev", "blank"
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
    "next": "next",
    "prev": "prev",
}


@dataclass(frozen=True)
class Command:
    kind: CommandKind
    arg: int | None = None


@dataclass(frozen=True)
class MoveText:
    text: str


def parse_input(line: str) -> Command | MoveText:
    tokens = line.strip().split()
    if not tokens:
        return Command("blank")
    head = tokens[0].lower()
    if head in _ALIASES:
        kind = _ALIASES[head]
        arg = None
        if kind == "replay" and len(tokens) > 1 and tokens[1].isdigit():
            arg = int(tokens[1])
        return Command(kind, arg)
    if head.isdigit() and len(tokens) == 1:
        return Command("replay", int(head))
    return MoveText(line.strip())
