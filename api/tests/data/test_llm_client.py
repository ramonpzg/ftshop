import json

import httpx
import pytest

from euro_chess_studio.data import llm_client


def install_transport(monkeypatch: pytest.MonkeyPatch, handler) -> None:
    real_client = httpx.Client
    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(
        llm_client.httpx,
        "Client",
        lambda **kwargs: real_client(transport=transport, **kwargs),
    )
    monkeypatch.setattr(llm_client.time, "sleep", lambda _delay: None)


def test_default_model_is_current(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    assert llm_client.get_llm_model() == "gpt-5.6-luna"


def test_chat_uses_chat_completions_and_json_mode(monkeypatch: pytest.MonkeyPatch):
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": '{"move":"e2e4"}'}}]})

    install_transport(monkeypatch, handler)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    result = llm_client.chat([{"role": "user", "content": "move"}], json_response=True)

    assert result == '{"move":"e2e4"}'
    assert seen["url"] == "https://api.openai.com/v1/chat/completions"
    assert seen["body"] == {
        "model": "gpt-5.6-luna",
        "reasoning_effort": "medium",
        "messages": [{"role": "user", "content": "move"}],
        "response_format": {"type": "json_object"},
    }


def test_json_mode_falls_back_after_400(monkeypatch: pytest.MonkeyPatch):
    bodies: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        if len(bodies) == 1:
            return httpx.Response(400, text="response_format is not supported")
        return httpx.Response(200, json={"choices": [{"message": {"content": "plain"}}]})

    install_transport(monkeypatch, handler)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    assert llm_client.chat([{"role": "user", "content": "move"}], json_response=True) == "plain"
    assert "response_format" in bodies[0]
    assert "response_format" not in bodies[1]


def test_generic_permissions_401_retries(monkeypatch: pytest.MonkeyPatch):
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(
                401,
                headers={"x-request-id": "req-transient"},
                json={
                    "error": {"message": "You have insufficient permissions for this operation."}
                },
            )
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    install_transport(monkeypatch, handler)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    assert llm_client.chat([{"role": "user", "content": "move"}]) == "ok"
    assert calls == 2


def test_explicit_invalid_key_401_does_not_retry(monkeypatch: pytest.MonkeyPatch):
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            401,
            headers={"x-request-id": "req-invalid"},
            json={"error": {"message": "Incorrect API key provided"}},
        )

    install_transport(monkeypatch, handler)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    with pytest.raises(llm_client.LlmRequestError, match="req-invalid"):
        llm_client.chat([{"role": "user", "content": "move"}])
    assert calls == 1
