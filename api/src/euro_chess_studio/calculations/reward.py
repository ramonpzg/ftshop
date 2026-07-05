"""Reward function for the chess RL environment.

Kept deliberately simple: it distinguishes SFT (learn what a good answer
looks like) from RL (learn what a good action does). The environment can
validate moves, so the reward can be computed exactly, not estimated.
"""


def compute_reward(*, legal: bool, is_check: bool, is_checkmate: bool) -> int:
    if not legal:
        return -1
    if is_checkmate:
        return 10
    if is_check:
        return 2
    return 1
