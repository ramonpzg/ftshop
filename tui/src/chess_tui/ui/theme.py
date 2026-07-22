"""The chalk theme. The palette is lifted from the deck's chalk style
(deck/style.css, html.style-chalk): near-black ground, light ink, one
restrained blue accent. Rich downgrades truecolor for older terminals;
NO_COLOR or --no-color selects PLAIN, which styles nothing. Case, not
color, carries the White/Black distinction, so nothing breaks without
color and no meaning is carried by color alone."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    ink: str
    soft: str
    faint: str
    accent: str
    good: str
    bad: str
    white_piece: str
    black_piece: str
    empty_square: str
    square_light: str
    square_dark: str
    square_last: str

    def square_background(self, is_light: bool, is_last_move: bool) -> str:
        if is_last_move:
            return self.square_last
        return self.square_light if is_light else self.square_dark


CHALK = Theme(
    ink="#f3f1ec",
    soft="#b9b5ac",
    faint="#85817a",
    accent="#7a9bff",
    good="#5fbf8a",
    bad="#e0796b",
    white_piece="bold #f3f1ec",
    black_piece="#b9b5ac",
    empty_square="#85817a",
    square_light="#3b3b42",  # the deck's board-dark token
    square_dark="#26262b",
    square_last="#46557f",  # desaturated accent for the last move
)

PLAIN = Theme(
    ink="",
    soft="",
    faint="",
    accent="",
    good="",
    bad="",
    white_piece="",
    black_piece="",
    empty_square="",
    square_light="",
    square_dark="",
    square_last="",
)


def pick_theme(no_color: bool) -> Theme:
    return PLAIN if no_color else CHALK
