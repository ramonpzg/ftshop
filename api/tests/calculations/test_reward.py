from euro_chess_studio.calculations.reward import compute_reward


def test_illegal_move_is_penalized():
    assert compute_reward(legal=False, is_check=False, is_checkmate=False) == -1


def test_legal_quiet_move():
    assert compute_reward(legal=True, is_check=False, is_checkmate=False) == 1


def test_legal_move_that_gives_check():
    assert compute_reward(legal=True, is_check=True, is_checkmate=False) == 2


def test_legal_move_that_delivers_checkmate():
    assert compute_reward(legal=True, is_check=True, is_checkmate=True) == 10


def test_illegal_move_ignores_check_and_checkmate_flags():
    # An illegal move can't actually be a checkmate; illegality always wins.
    assert compute_reward(legal=False, is_check=True, is_checkmate=True) == -1
