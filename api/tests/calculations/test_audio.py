from euro_chess_studio.calculations.audio import synthesize_spectrogram


def test_synthesize_spectrogram_has_requested_shape():
    grid = synthesize_spectrogram(0.4, ["capture", "wood"], bins=4, frames=3)
    assert len(grid) == 3
    for row in grid:
        assert len(row) == 4


def test_synthesize_spectrogram_is_deterministic():
    a = synthesize_spectrogram(0.4, ["capture", "wood"])
    b = synthesize_spectrogram(0.4, ["capture", "wood"])
    assert a == b


def test_synthesize_spectrogram_varies_with_tags():
    a = synthesize_spectrogram(0.4, ["capture"])
    b = synthesize_spectrogram(0.4, ["move"])
    assert a != b


def test_synthesize_spectrogram_values_are_non_negative():
    grid = synthesize_spectrogram(0.4, ["capture", "wood", "impact"])
    for row in grid:
        for value in row:
            assert value >= 0
