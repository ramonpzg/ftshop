"""Boundary tests for the Chat Completions transport, against a mock
HTTP transport. This tests the data boundary itself, not the app."""

import json

import httpx
import pytest

from euro_chess_studio.data import llm_client


@pytest.fixture(autouse=True)
def clean_slate(monkeypatch: pytest.MonkeyPatch):
    llm_client.reset_credential_memory()
    monkeypatch.delenv("OPENAI_RECENT_KEY_401_RETRY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("VIDEO_PROMPT_API_KEY", raising=False)
    monkeypatch.delenv("VIDEO_PROMPT_BASE_URL", raising=False)
    monkeypatch.delenv("VIDEO_PROMPT_MODEL", raising=False)
    yield
    llm_client.reset_credential_memory()


def install_transport(monkeypatch: pytest.MonkeyPatch, handler) -> list[float]:
    """Routes httpx through a MockTransport and records backoff sleeps."""
    real_client = httpx.Client
    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(
        llm_client.httpx,
        "Client",
        lambda **kwargs: real_client(transport=transport, **kwargs),
    )
    sleeps: list[float] = []
    monkeypatch.setattr(llm_client.time, "sleep", sleeps.append)
    return sleeps


def ok_response(content: str = "ok") -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})


class _FakeClock:
    """A monotonic clock the test controls, so deadline arithmetic can
    be verified precisely without waiting on real wall time. `sleep`
    advances the clock instead of blocking, matching what a real sleep
    would do to the budget."""

    def __init__(self) -> None:
        self.now = 0.0

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


def install_fake_clock(monkeypatch: pytest.MonkeyPatch) -> _FakeClock:
    clock = _FakeClock()
    monkeypatch.setattr(llm_client.time, "monotonic", clock.monotonic)
    monkeypatch.setattr(llm_client.time, "sleep", clock.sleep)
    return clock


def install_mock_client(monkeypatch: pytest.MonkeyPatch, handler) -> None:
    """Like install_transport, but leaves time.sleep alone so a
    fake-clock test can control it instead."""
    real_client = httpx.Client
    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(
        llm_client.httpx,
        "Client",
        lambda **kwargs: real_client(transport=transport, **kwargs),
    )


def test_default_model_is_current():
    assert llm_client.get_llm_model() == "gpt-5.6-luna"


def test_video_prompt_model_defaults_to_luna():
    assert llm_client.get_video_prompt_model() == "gpt-5.6-luna"


def test_chat_uses_chat_completions_and_json_mode(monkeypatch: pytest.MonkeyPatch):
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content)
        return ok_response('{"move":"e2e4"}')

    install_transport(monkeypatch, handler)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    outcome = llm_client.chat([{"role": "user", "content": "move"}], json_response=True)

    assert outcome.content == '{"move":"e2e4"}'
    assert outcome.attempts == 1
    assert outcome.provider_alias == "opponent"
    assert outcome.json_mode_sent and not outcome.json_mode_dropped
    assert seen["url"] == "https://api.openai.com/v1/chat/completions"
    assert seen["body"] == {
        "model": "gpt-5.6-luna",
        "reasoning_effort": "medium",
        "messages": [{"role": "user", "content": "move"}],
        "response_format": {"type": "json_object"},
    }


def test_base_url_trailing_slash_is_stripped(monkeypatch: pytest.MonkeyPatch):
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        return ok_response()

    install_transport(monkeypatch, handler)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "http://127.0.0.1:8080/v1/")

    llm_client.chat([{"role": "user", "content": "hi"}])
    assert seen["url"] == "http://127.0.0.1:8080/v1/chat/completions"


def test_malformed_response_shape_fails_with_excerpt(monkeypatch: pytest.MonkeyPatch):
    install_transport(monkeypatch, lambda _req: httpx.Response(200, json={"unexpected": True}))
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    with pytest.raises(llm_client.LlmRequestError, match="unexpected llm response shape"):
        llm_client.chat([{"role": "user", "content": "move"}])


def test_json_mode_rejection_then_success(monkeypatch: pytest.MonkeyPatch):
    bodies: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        if len(bodies) == 1:
            return httpx.Response(
                400, json={"error": {"message": "response_format is not supported"}}
            )
        return ok_response("plain")

    install_transport(monkeypatch, handler)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    outcome = llm_client.chat([{"role": "user", "content": "move"}], json_response=True)
    assert outcome.content == "plain"
    assert outcome.json_mode_dropped is True
    assert "response_format" in bodies[0]
    assert "response_format" not in bodies[1]


def test_unrelated_400_is_not_treated_as_response_format(monkeypatch: pytest.MonkeyPatch):
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(400, json={"error": {"message": "messages must not be empty"}})

    install_transport(monkeypatch, handler)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    with pytest.raises(llm_client.LlmRequestError, match="messages must not be empty"):
        llm_client.chat([{"role": "user", "content": "move"}], json_response=True)
    assert calls == 1


def test_catalog_omits_reasoning_effort_for_local_gemma(monkeypatch: pytest.MonkeyPatch):
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content)
        return ok_response()

    install_transport(monkeypatch, handler)
    monkeypatch.setenv("OPENAI_API_KEY", "local")
    monkeypatch.setenv("OPENAI_BASE_URL", "http://127.0.0.1:8080/v1")
    monkeypatch.setenv("OPENAI_MODEL", "gemma-4-2b-local")

    llm_client.chat([{"role": "user", "content": "move"}])
    assert "reasoning_effort" not in seen["body"]


def test_reasoning_effort_rejection_falls_back_once(monkeypatch: pytest.MonkeyPatch):
    bodies: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        if len(bodies) == 1:
            return httpx.Response(
                400, json={"error": {"message": "Unknown parameter: reasoning_effort"}}
            )
        return ok_response()

    install_transport(monkeypatch, handler)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    outcome = llm_client.chat([{"role": "user", "content": "move"}])
    assert outcome.reasoning_effort_dropped is True
    assert "reasoning_effort" in bodies[0]
    assert "reasoning_effort" not in bodies[1]


def test_429_retries_and_honours_retry_after(monkeypatch: pytest.MonkeyPatch):
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(429, headers={"retry-after": "7"}, text="slow down")
        return ok_response()

    sleeps = install_transport(monkeypatch, handler)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    outcome = llm_client.chat([{"role": "user", "content": "move"}])
    assert outcome.attempts == 2
    assert sleeps == [7.0]


def test_500_exhaustion_raises_after_bounded_retries(monkeypatch: pytest.MonkeyPatch):
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(500, headers={"x-request-id": f"req-{calls}"}, text="boom")

    install_transport(monkeypatch, handler)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    with pytest.raises(llm_client.LlmRequestError) as excinfo:
        llm_client.chat([{"role": "user", "content": "move"}])
    assert calls == 3
    assert excinfo.value.request_ids == ("req-1", "req-2", "req-3")


def test_transport_timeout_retries_then_raises(monkeypatch: pytest.MonkeyPatch):
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ConnectTimeout("connection timed out")

    install_transport(monkeypatch, handler)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    with pytest.raises(llm_client.LlmRequestError, match="could not reach"):
        llm_client.chat([{"role": "user", "content": "move"}])
    assert calls == 3


def test_deadline_bounds_total_time_regardless_of_transport_retries(
    monkeypatch: pytest.MonkeyPatch,
):
    """Reproduces the reported bug: `timeout` used to be handed
    unchanged to every one of up to three HTTP attempts, so a short
    overall deadline could take several times as long once transport
    retries and backoff stacked up. Every attempt here "costs" 0.1s of
    simulated time before failing; a 0.2s deadline must stop asking
    once that 0.2s is spent, not run the full retry ladder anyway."""
    clock = install_fake_clock(monkeypatch)
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        clock.now += 0.1
        raise httpx.ConnectTimeout("connection timed out")

    install_mock_client(monkeypatch, handler)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    with pytest.raises(llm_client.LlmRequestError):
        llm_client.chat([{"role": "user", "content": "move"}], timeout=0.2)

    # Only the first attempt actually reached the transport: its 0.1s
    # cost plus one backoff sleep -- capped to the 0.1s left of the
    # deadline -- spends the whole 0.2s budget, so a second attempt
    # never starts. The old behaviour ran the full retry ladder (three
    # attempts, uncapped backoff) regardless of how little was left.
    assert calls == 1
    assert clock.now == pytest.approx(0.2)


def test_remaining_deadline_shrinks_and_is_passed_to_each_transport_attempt(
    monkeypatch: pytest.MonkeyPatch,
):
    """The transport must see the true remaining budget on each retry,
    not the original per-call timeout replayed unchanged -- otherwise
    a later attempt could itself block for the full original timeout
    even though the overall deadline is nearly spent."""
    clock = install_fake_clock(monkeypatch)
    seen_timeouts: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_timeouts.append(request.extensions["timeout"]["connect"])
        clock.now += 1.0
        if len(seen_timeouts) == 1:
            return httpx.Response(500, text="boom")
        return ok_response()

    install_mock_client(monkeypatch, handler)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    llm_client.chat([{"role": "user", "content": "move"}], timeout=10.0)

    assert seen_timeouts[0] == pytest.approx(10.0)
    # After the first attempt's 1.0s cost and its backoff sleep, the
    # second attempt gets strictly less than the original 10.0s: proof
    # the shrinking deadline, not the original timeout, reaches the
    # transport on every attempt.
    assert seen_timeouts[1] < seen_timeouts[0]


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
    monkeypatch.setenv("OPENAI_API_KEY", "sk-secret-key")
    monkeypatch.setenv("OPENAI_RECENT_KEY_401_RETRY", "1")

    with pytest.raises(llm_client.LlmRequestError, match="req-invalid"):
        llm_client.chat([{"role": "user", "content": "move"}])
    assert calls == 1


def test_generic_401_without_evidence_does_not_retry(monkeypatch: pytest.MonkeyPatch):
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            401,
            json={"error": {"message": "You have insufficient permissions for this operation."}},
        )

    install_transport(monkeypatch, handler)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    with pytest.raises(llm_client.LlmRequestError):
        llm_client.chat([{"role": "user", "content": "move"}])
    assert calls == 1


def test_generic_401_with_opt_in_retries_then_succeeds(monkeypatch: pytest.MonkeyPatch):
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
        return ok_response()

    install_transport(monkeypatch, handler)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_RECENT_KEY_401_RETRY", "1")

    outcome = llm_client.chat([{"role": "user", "content": "move"}])
    assert outcome.content == "ok"
    assert calls == 2
    assert outcome.request_ids == ("req-transient",)


def test_generic_401_with_in_process_success_evidence_retries(monkeypatch: pytest.MonkeyPatch):
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 2:
            return httpx.Response(
                401,
                json={
                    "error": {"message": "You have insufficient permissions for this operation."}
                },
            )
        return ok_response()

    install_transport(monkeypatch, handler)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    # First call succeeds, which is the evidence the second call uses.
    llm_client.chat([{"role": "user", "content": "one"}])
    outcome = llm_client.chat([{"role": "user", "content": "two"}])
    assert outcome.content == "ok"
    assert calls == 3


def test_exhausted_generic_401_retains_every_request_id(monkeypatch: pytest.MonkeyPatch):
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            401,
            headers={"x-request-id": f"req-{calls}"},
            json={"error": {"message": "You have insufficient permissions for this operation."}},
        )

    install_transport(monkeypatch, handler)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_RECENT_KEY_401_RETRY", "1")

    with pytest.raises(llm_client.LlmRequestError) as excinfo:
        llm_client.chat([{"role": "user", "content": "move"}])
    assert calls == 3
    assert excinfo.value.request_ids == ("req-1", "req-2", "req-3")


def test_diagnostics_never_contain_the_api_key(monkeypatch: pytest.MonkeyPatch):
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": "Incorrect API key provided"}})

    install_transport(monkeypatch, handler)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-super-secret")

    with pytest.raises(llm_client.LlmRequestError) as excinfo:
        llm_client.chat([{"role": "user", "content": "the position is secret too"}])
    assert "sk-super-secret" not in str(excinfo.value)
    assert "the position is secret too" not in str(excinfo.value)


def test_local_gemma_and_hosted_luna_do_not_leak_into_each_other(
    monkeypatch: pytest.MonkeyPatch,
):
    requests: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(
            {
                "url": str(request.url),
                "authorization": request.headers["authorization"],
                "body": json.loads(request.content),
            }
        )
        return ok_response("{}")

    install_transport(monkeypatch, handler)
    monkeypatch.setenv("OPENAI_API_KEY", "local-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "http://127.0.0.1:8080/v1")
    monkeypatch.setenv("OPENAI_MODEL", "gemma-4-2b-local")
    monkeypatch.setenv("VIDEO_PROMPT_API_KEY", "luna-key")
    monkeypatch.setenv("VIDEO_PROMPT_BASE_URL", "https://api.openai.com/v1")
    monkeypatch.setenv("VIDEO_PROMPT_MODEL", "gpt-5.6-luna")

    move = llm_client.chat([{"role": "user", "content": "move"}], json_response=True)
    scene = llm_client.video_prompt_chat([{"role": "user", "content": "scene"}])

    assert move.provider_alias == "opponent"
    assert scene.provider_alias == "video_prompt"
    opponent_request, scene_request = requests
    assert opponent_request["url"] == "http://127.0.0.1:8080/v1/chat/completions"
    assert opponent_request["authorization"] == "Bearer local-key"
    assert opponent_request["body"]["model"] == "gemma-4-2b-local"
    assert "reasoning_effort" not in opponent_request["body"]
    assert scene_request["url"] == "https://api.openai.com/v1/chat/completions"
    assert scene_request["authorization"] == "Bearer luna-key"
    assert scene_request["body"]["model"] == "gpt-5.6-luna"
    assert scene_request["body"]["reasoning_effort"] == "medium"
