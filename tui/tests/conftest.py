"""Shared fixtures. Real SQLite in a temp directory and a scripted
httpx.MockTransport at the transport boundary; nothing above the
transport is mocked."""

import json
import sqlite3
from pathlib import Path

import httpx
import pytest

from chess_tui.data.config import Config
from chess_tui.data.db import connect
from chess_tui.data.llm_client import LlmClient


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "games.db"


@pytest.fixture
def conn(db_path: Path):
    connection = connect(db_path)
    yield connection
    connection.close()


@pytest.fixture
def config(db_path: Path) -> Config:
    return Config(db_path=db_path, no_color=True, player_name="tester")


def chat_response(content: str) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "id": "chatcmpl-test",
            "choices": [{"message": {"role": "assistant", "content": content}}],
        },
    )


def move_reply(move: str, comment: str = "Noted.") -> str:
    return json.dumps({"move": move, "comment": comment})


class ScriptedTransport:
    """Answers requests from a script. An entry can be a content
    string, a prebuilt httpx.Response, or an exception to raise."""

    def __init__(self, script: list):
        self.script = list(script)
        self.requests: list[httpx.Request] = []

    def transport(self) -> httpx.MockTransport:
        def handler(request: httpx.Request) -> httpx.Response:
            self.requests.append(request)
            if not self.script:
                raise AssertionError("model called more often than scripted")
            item = self.script.pop(0)
            if isinstance(item, Exception):
                raise item
            if isinstance(item, httpx.Response):
                return item
            return chat_response(item)

        return httpx.MockTransport(handler)


def scripted_client(config: Config, script: list) -> tuple[LlmClient, ScriptedTransport]:
    scripted = ScriptedTransport(script)
    return LlmClient(config, transport=scripted.transport()), scripted


def fresh_connection(db_path: Path) -> sqlite3.Connection:
    """A second, independent connection, for asserting what actually
    committed rather than what this connection can still see."""
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection
