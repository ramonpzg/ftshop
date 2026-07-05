"""Pure calculation illustrating how a chess sound event turns into a
spectrogram-like grid. Deterministic and tiny -- not a real audio pipeline,
just enough structure for the workshop's audio artifact panel to show
something real rather than a placeholder image.
"""

import math


def synthesize_spectrogram(
    duration_seconds: float,
    tags: list[str],
    bins: int = 8,
    frames: int = 8,
) -> list[list[float]]:
    seed = sum(sum(ord(c) for c in tag) for tag in tags) or 1
    grid = []
    for frame in range(frames):
        row = []
        for band in range(bins):
            value = abs(math.sin((seed + frame * bins + band) * 0.37)) * duration_seconds
            row.append(round(value, 3))
        grid.append(row)
    return grid
