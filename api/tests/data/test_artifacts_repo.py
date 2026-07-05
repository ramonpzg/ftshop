from pathlib import Path

from euro_chess_studio.data.artifacts_repo import insert_artifact, list_artifacts
from euro_chess_studio.data.db import get_connection, init_db


def make_conn(tmp_path: Path):
    conn = get_connection(tmp_path / "test.db")
    init_db(conn)
    return conn


def test_insert_artifact_round_trips_payload(tmp_path: Path):
    conn = make_conn(tmp_path)
    row = insert_artifact(
        conn,
        job_config_id=None,
        modality="text",
        kind="prompt_eval",
        payload={"legal_move_rate": 1.0},
        cached=False,
    )
    assert row["modality"] == "text"
    assert row["cached"] == 0
    assert '"legal_move_rate"' in row["payload_json"]


def test_list_artifacts_filters_by_modality(tmp_path: Path):
    conn = make_conn(tmp_path)
    insert_artifact(conn, job_config_id=None, modality="text", kind="a", payload={}, cached=True)
    insert_artifact(conn, job_config_id=None, modality="image", kind="b", payload={}, cached=True)
    assert len(list_artifacts(conn, "text")) == 1
    assert len(list_artifacts(conn)) == 2


def test_list_artifacts_orders_most_recent_first(tmp_path: Path):
    conn = make_conn(tmp_path)
    first = insert_artifact(
        conn, job_config_id=None, modality="text", kind="a", payload={}, cached=True
    )
    second = insert_artifact(
        conn, job_config_id=None, modality="text", kind="b", payload={}, cached=True
    )
    rows = list_artifacts(conn, "text")
    assert rows[0]["id"] == second["id"]
    assert rows[1]["id"] == first["id"]
