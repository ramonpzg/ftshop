"""Static definition of the five workshop pages.

Mirrors web/src/lib/pages.ts. Duplicated deliberately: this is five rows of
static data, not worth sharing a codegen pipeline over for a v0.
"""

from dataclasses import dataclass

Modality = str  # one of "meta", "text", "image", "audio", "video"


@dataclass(frozen=True)
class PageDef:
    slug: str
    title: str
    modality: Modality
    order_index: int


PAGES: list[PageDef] = [
    PageDef("presentation", "Presentation", "meta", 0),
    PageDef("chess-machine", "Building a Chess Machine", "text", 1),
    PageDef("painting-pieces", "Painting Our Pieces", "image", 2),
    PageDef("board-sound", "Giving the Board Sound", "audio", 3),
    PageDef("real-world-video", "Video of the Real-World Use Case", "video", 4),
]
