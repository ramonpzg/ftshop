"""The llama.cpp HTTP boundary. One place makes the Chat Completions
request; everything above it works with ChatReply or TransportFailure.

The endpoint is {base_url}/chat/completions, llama.cpp's
OpenAI-compatible API. No Responses API, no streaming, no
reasoning_effort: thinking is the server's business (--reasoning off).
Diagnostics never contain the API key."""

import json
import time
from dataclasses import dataclass
from typing import Literal

import httpx

from chess_tui.data.config import Config

FailureKind = Literal["unreachable", "timeout", "http_error"]

_BODY_EXCERPT = 200


@dataclass(frozen=True)
class ChatReply:
    content: str
    request_id: str | None
    latency_ms: int


class TransportFailure(Exception):
    def __init__(
        self,
        kind: FailureKind,
        detail: str,
        latency_ms: int,
        request_id: str | None = None,
    ) -> None:
        super().__init__(detail)
        self.kind = kind
        self.detail = detail
        self.latency_ms = latency_ms
        self.request_id = request_id


class LlmClient:
    """Owns the single httpx.Client. transport is injectable so tests
    exercise this boundary with httpx.MockTransport instead of mocking
    the application above it."""

    def __init__(self, config: Config, transport: httpx.BaseTransport | None = None) -> None:
        self._url = f"{config.base_url}/chat/completions"
        self._model = config.model
        self._client = httpx.Client(
            headers={"Authorization": f"Bearer {config.api_key}"},
            timeout=httpx.Timeout(config.timeout_seconds, connect=10.0),
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def request_move(self, messages: list[dict], grammar: str) -> ChatReply:
        """One fresh, bounded, non-streaming request per turn. The
        constraint rides as llama.cpp's raw GBNF `grammar` field, which
        far older server builds honor than response_format json_schema;
        Ramon's Termux build ignored the latter, free-ran to the token
        cap, and returned junk. A non-llama.cpp server ignores the
        field, and the corrective/retry machinery upstream covers that
        honestly."""
        body = {
            "model": self._model,
            "messages": messages,
            "grammar": grammar,
            "temperature": 0.3,
            "max_tokens": 192,
            "stream": False,
        }
        started = time.monotonic()
        try:
            response = self._client.post(self._url, json=body)
        except httpx.TimeoutException as error:
            raise TransportFailure(
                "timeout",
                f"no reply from {self._url}",
                _elapsed_ms(started),
            ) from error
        except httpx.TransportError as error:
            raise TransportFailure(
                "unreachable",
                f"{self._url}: {error.__class__.__name__}",
                _elapsed_ms(started),
            ) from error

        latency = _elapsed_ms(started)
        request_id = response.headers.get("x-request-id")
        if response.status_code != 200:
            excerpt = response.text[:_BODY_EXCERPT]
            raise TransportFailure(
                "http_error",
                f"HTTP {response.status_code}: {excerpt}",
                latency,
                request_id,
            )
        try:
            data = response.json()
        except (json.JSONDecodeError, ValueError) as error:
            raise TransportFailure(
                "http_error",
                "unreadable response body",
                latency,
                request_id,
            ) from error
        content = _content_of(data)
        return ChatReply(
            content=content,
            request_id=request_id or _body_id(data),
            latency_ms=latency,
        )


def _elapsed_ms(started: float) -> int:
    return int((time.monotonic() - started) * 1000)


def _content_of(data: object) -> str:
    """choices[0].message.content, defensively. A 200 with a missing or
    null content is judged upstream as an empty reply, not crashed on."""
    if not isinstance(data, dict):
        return ""
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    return content if isinstance(content, str) else ""


def _body_id(data: object) -> str | None:
    if isinstance(data, dict):
        value = data.get("id")
        if isinstance(value, str):
            return value
    return None
