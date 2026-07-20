"""Deterministic move vocabulary for the board-tensor dataset rows.

Every UCI move maps to one integer class and back:

    class = from_square * 320 + to_square * 5 + promotion_code

Squares index a1=0 to h8=63 (rank * 8 + file). Promotion codes: 0 none,
1 queen, 2 rook, 3 bishop, 4 knight. Vocabulary size 64 * 64 * 5 =
20480. Most classes are unreachable in chess (a1a1, promotions off the
back ranks); that is normal for enumerated move vocabularies and does
not hurt a classifier, it just wastes logits. AlphaZero's 8x8x73 planes
are a tighter encoding of the same idea; this one is chosen because a
workshop attendee can invert it in their head.
"""

PROMOTION_CODES = {"": 0, "q": 1, "r": 2, "b": 3, "n": 4}
_PROMOTION_BY_CODE = {code: piece for piece, code in PROMOTION_CODES.items()}
VOCABULARY_SIZE = 64 * 64 * 5
MOVE_VOCABULARY = "from_square * 320 + to_square * 5 + promotion_code"


def square_index(square: str) -> int:
    """a1 -> 0, h1 -> 7, a2 -> 8, h8 -> 63."""
    file = ord(square[0]) - ord("a")
    rank = int(square[1]) - 1
    if not (0 <= file <= 7 and 0 <= rank <= 7):
        raise ValueError(f"not a square: {square}")
    return rank * 8 + file


def move_class_index(uci: str) -> int:
    """The class index for a syntactically valid UCI move."""
    if len(uci) not in (4, 5):
        raise ValueError(f"not a UCI move: {uci}")
    promotion = uci[4:] if len(uci) == 5 else ""
    if promotion not in PROMOTION_CODES:
        raise ValueError(f"not a promotion piece: {promotion}")
    return square_index(uci[0:2]) * 320 + square_index(uci[2:4]) * 5 + PROMOTION_CODES[promotion]


def move_from_class(index: int) -> str:
    """The inverse mapping, for teaching that the class is not arbitrary."""
    if not (0 <= index < VOCABULARY_SIZE):
        raise ValueError(f"class out of range: {index}")
    from_square, rest = divmod(index, 320)
    to_square, promotion_code = divmod(rest, 5)

    def square_name(square: int) -> str:
        return f"{chr(ord('a') + square % 8)}{square // 8 + 1}"

    return square_name(from_square) + square_name(to_square) + _PROMOTION_BY_CODE[promotion_code]
