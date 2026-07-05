"""Pure calculation for uniform frame sampling, the same math a real
video fine-tuning pipeline uses to pick a fixed number of frames from a
clip of arbitrary length.
"""


def uniform_frame_indices(total_frames: int, num_samples: int) -> list[int]:
    if total_frames <= 0 or num_samples <= 0:
        raise ValueError("total_frames and num_samples must be positive")
    if num_samples >= total_frames:
        return list(range(total_frames))
    step = total_frames / num_samples
    return [int(i * step) for i in range(num_samples)]
