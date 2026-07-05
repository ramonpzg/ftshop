import pytest

from euro_chess_studio.calculations.video import uniform_frame_indices


def test_uniform_frame_indices_spans_the_full_clip():
    indices = uniform_frame_indices(100, 5)
    assert indices == [0, 20, 40, 60, 80]


def test_uniform_frame_indices_returns_all_frames_when_samples_exceed_total():
    assert uniform_frame_indices(4, 10) == [0, 1, 2, 3]


def test_uniform_frame_indices_rejects_non_positive_inputs():
    with pytest.raises(ValueError):
        uniform_frame_indices(0, 5)
    with pytest.raises(ValueError):
        uniform_frame_indices(100, 0)
