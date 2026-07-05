from euro_chess_studio.calculations.ids import generate_id, workspace_shape_id


def test_generate_id_uses_prefix():
    assert generate_id("user").startswith("user_")


def test_generate_id_is_unique():
    ids = {generate_id("user") for _ in range(200)}
    assert len(ids) == 200


def test_workspace_shape_id_is_deterministic():
    assert workspace_shape_id("user_1", "chess-machine") == workspace_shape_id(
        "user_1", "chess-machine"
    )


def test_workspace_shape_id_differs_by_page():
    assert workspace_shape_id("user_1", "chess-machine") != workspace_shape_id(
        "user_1", "painting-pieces"
    )
