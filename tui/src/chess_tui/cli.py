"""Entry point. Flags mirror the CHESS_TUI_* environment variables;
flags win. The API key is accepted and sent, never persisted or
displayed."""

import argparse
import os

from chess_tui import __version__
from chess_tui.data.config import (
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    DEFAULT_TIMEOUT_SECONDS,
    load_config,
)
from chess_tui.data.db import connect
from chess_tui.data.llm_client import LlmClient
from chess_tui.ui.app import App


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="chess-tui",
        description="Play chess against a local llama.cpp model in the terminal.",
    )
    parser.add_argument("--base-url", help=f"OpenAI-compatible base URL ({DEFAULT_BASE_URL})")
    parser.add_argument("--model", help=f"served model alias ({DEFAULT_MODEL})")
    parser.add_argument("--api-key", help="bearer token; the local server needs none")
    parser.add_argument(
        "--timeout",
        type=float,
        help=f"model reply timeout in seconds ({DEFAULT_TIMEOUT_SECONDS:.0f})",
    )
    parser.add_argument("--db", help="SQLite path (default: XDG data dir)")
    parser.add_argument("--no-color", action="store_true", help="plain output; NO_COLOR works too")
    parser.add_argument("--version", action="version", version=f"chess-tui {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_config(
        os.environ,
        base_url=args.base_url,
        model=args.model,
        api_key=args.api_key,
        timeout=args.timeout,
        db=args.db,
        no_color=args.no_color,
    )
    conn = connect(config.db_path)
    client = LlmClient(config)
    try:
        App(config, conn, client).run()
    finally:
        client.close()
        conn.close()
    return 0
