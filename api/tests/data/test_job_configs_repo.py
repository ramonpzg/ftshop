import json
from pathlib import Path

from euro_chess_studio.data.db import get_connection, init_db
from euro_chess_studio.data.job_configs_repo import insert_job_config


def make_conn(tmp_path: Path):
    conn = get_connection(tmp_path / "test.db")
    init_db(conn)
    return conn


def test_insert_job_config_round_trips_params(tmp_path: Path):
    conn = make_conn(tmp_path)
    row = insert_job_config(
        conn, workspace_id=None, job_type="audio.make_spectrogram", params={"duration": 0.4}
    )
    assert row["job_type"] == "audio.make_spectrogram"
    assert json.loads(row["params_json"]) == {"duration": 0.4}
