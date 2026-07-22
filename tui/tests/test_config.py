"""Configuration precedence, base URL normalization, and the data
directory default."""

from pathlib import Path

from chess_tui.cli import build_parser
from chess_tui.data.config import default_db_path, load_config, normalize_base_url


def test_defaults(tmp_path):
    config = load_config({"CHESS_TUI_DB": str(tmp_path / "x.db")})
    assert config.base_url == "http://127.0.0.1:9017/v1"
    assert config.model == "gemma-4-2b-local"
    assert config.api_key == "local"
    assert config.timeout_seconds == 120.0
    assert config.no_color is False
    assert config.player_name is None


def test_environment_overrides():
    env = {
        "CHESS_TUI_BASE_URL": "http://127.0.0.1:9999/v1/",
        "CHESS_TUI_MODEL": "other-alias",
        "CHESS_TUI_API_KEY": "k",
        "CHESS_TUI_TIMEOUT": "30",
        "CHESS_TUI_DB": "/tmp/elsewhere.db",
    }
    config = load_config(env)
    assert config.base_url == "http://127.0.0.1:9999/v1"  # trailing slash gone
    assert config.model == "other-alias"
    assert config.timeout_seconds == 30.0
    assert config.db_path == Path("/tmp/elsewhere.db")


def test_flags_beat_environment():
    env = {"CHESS_TUI_MODEL": "from-env", "CHESS_TUI_DB": "/tmp/env.db"}
    config = load_config(env, model="from-flag", db="/tmp/flag.db", timeout=5.0)
    assert config.model == "from-flag"
    assert config.db_path == Path("/tmp/flag.db")
    assert config.timeout_seconds == 5.0


def test_no_color_env_variable_is_honored():
    assert load_config({"NO_COLOR": "1", "CHESS_TUI_DB": "/tmp/x.db"}).no_color is True
    assert load_config({"CHESS_TUI_DB": "/tmp/x.db"}).no_color is False


def test_normalize_base_url_strips_once_and_only_trailing():
    assert normalize_base_url("http://h:8080/v1/") == "http://h:8080/v1"
    assert normalize_base_url("  http://h:8080/v1  ") == "http://h:8080/v1"
    assert normalize_base_url("http://h:8080/v1") == "http://h:8080/v1"


def test_default_db_path_honors_xdg():
    path = default_db_path({"XDG_DATA_HOME": "/data/xdg"})
    assert path == Path("/data/xdg/chess-tui/games.db")


def test_default_db_path_falls_back_to_home(monkeypatch):
    monkeypatch.setenv("HOME", "/home/somebody")
    path = default_db_path({})
    assert str(path).endswith(".local/share/chess-tui/games.db")


def test_parser_exposes_equivalent_flags():
    parser = build_parser()
    args = parser.parse_args(
        [
            "--base-url",
            "http://x/v1",
            "--model",
            "m",
            "--api-key",
            "k",
            "--timeout",
            "9",
            "--db",
            "/tmp/d.db",
            "--no-color",
        ]
    )
    assert args.base_url == "http://x/v1"
    assert args.model == "m"
    assert args.api_key == "k"
    assert args.timeout == 9.0
    assert args.db == "/tmp/d.db"
    assert args.no_color is True


def test_tall_mode_default_env_flag_and_validation():
    env = {"CHESS_TUI_DB": "/tmp/x.db"}
    assert load_config(env).tall_mode == "auto"
    assert load_config({**env, "CHESS_TUI_TALL": "always"}).tall_mode == "always"
    assert load_config({**env, "CHESS_TUI_TALL": "NEVER"}).tall_mode == "never"
    assert load_config({**env, "CHESS_TUI_TALL": "sideways"}).tall_mode == "auto"
    assert load_config(env, tall="never").tall_mode == "never"


def test_parser_has_tall_flag():
    args = build_parser().parse_args(["--tall", "always"])
    assert args.tall == "always"


def test_name_env_and_flag():
    env = {"CHESS_TUI_NAME": "enviro", "CHESS_TUI_DB": "/tmp/x.db"}
    assert load_config(env).player_name == "enviro"
    assert load_config(env, name="flagged").player_name == "flagged"


def test_parser_has_name_flag():
    args = build_parser().parse_args(["--name", "ramon"])
    assert args.name == "ramon"


def test_api_key_never_appears_in_repr():
    config = load_config({"CHESS_TUI_API_KEY": "sk-hidden", "CHESS_TUI_DB": "/tmp/x.db"})
    assert "sk-hidden" not in repr(config)
    assert "sk-hidden" not in str(config)
