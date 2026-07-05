from euro_chess_studio.calculations.ids import generate_id


def test_generate_id_uses_prefix():
    assert generate_id("user").startswith("user_")


def test_generate_id_is_unique():
    ids = {generate_id("user") for _ in range(200)}
    assert len(ids) == 200
