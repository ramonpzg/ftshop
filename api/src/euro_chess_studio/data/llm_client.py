"""OpenAI-compatible Chat Completions client. No business logic here.

Every text-model call in the app goes through this one transport:
opponent moves, scenario assessments, and future text jobs. It always
calls `/chat/completions`; the Responses API is not used anywhere.

Configured entirely through the environment so the presenter can point
it at api.openai.com today and any compatible endpoint (OpenRouter,
Hugging Face router, vLLM, llama.cpp) later without touching code:

    OPENAI_API_KEY    required
    OPENAI_BASE_URL   default https://api.openai.com/v1
    OPENAI_MODEL      default gpt-5.6-luna; the default opponent
    OPPONENT_MODELS   optional comma-separated list of extra opponents
                      to offer in the Start game picker, e.g.
                      google/gemma-4-E2B-it-qat-q4_0-gguf,gpt-5.6-luna

The video-scene prompt can use a separate compatible endpoint. Each
VIDEO_PROMPT_* setting falls back to its OPENAI_* counterpart:

    VIDEO_PROMPT_API_KEY
    VIDEO_PROMPT_BASE_URL
    VIDEO_PROMPT_MODEL default gpt-5.6-luna

Retry policy: 429, 5xx, and transport failures retry with bounded
exponential backoff, jitter, and Retry-After where supplied. A 401
normally fails immediately. The one exception, observed during the
workshop while a freshly created project key propagated: the exact
generic message "You have insufficient permissions for this operation"
may be retried, but only with evidence that the credential is real --
either the same credential already succeeded in this process, or the
operator set OPENAI_RECENT_KEY_401_RETRY=1 after creating or rotating
a key. Invalid-key, revoked-key, IP-policy, and project/model-denial
responses never retry. Deterministic 400s never retry, except one
narrow capability fallback each for response_format and
reasoning_effort when the provider's error names that exact field.
"""

import hashlib
import os
import random
import time
from dataclasses import dataclass

import httpx

from euro_chess_studio.calculations.model_catalog import build_chat_body

DEFAULT_MODEL = "gpt-5.6-luna"
TRANSIENT_PERMISSION_ERROR = "You have insufficient permissions for this operation"
MAX_TIMEOUT_SECONDS = 120.0
MAX_TRANSIENT_RETRIES = 2
MAX_PERMISSION_RETRIES = 2
RETRY_AFTER_CAP_SECONDS = 30.0
ERROR_EXCERPT_CHARS = 400

# Credentials that returned a 200 in this process, stored as salted-free
# sha256 fingerprints of (base_url, key). Evidence for the narrow
# transient-401 retry; never the key itself.
_working_credentials: set[str] = set()


class LlmNotConfiguredError(RuntimeError):
    pass


class LlmRequestError(RuntimeError):
    """A chat completion failed. Carries the provider request ids and
    status, plus whatever transport-attempt count and capability-fallback
    provenance had already accumulated before the failure -- the same
    diagnostics ChatOutcome carries for a success, so a terminal failure
    does not lose evidence that JSON mode or reasoning_effort was
    dropped just because the call went on to fail anyway. Never contains
    the API key or the full prompt."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        request_ids: tuple[str, ...] = (),
        transport_attempts: int | None = None,
        json_mode_dropped: bool = False,
        reasoning_effort_dropped: bool = False,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.request_ids = request_ids
        self.transport_attempts = transport_attempts
        self.json_mode_dropped = json_mode_dropped
        self.reasoning_effort_dropped = reasoning_effort_dropped


@dataclass(frozen=True)
class LlmSettings:
    """One resolved provider profile. `profile` is the provider alias
    recorded in provenance: "opponent" or "video_prompt"."""

    profile: str
    base_url: str
    api_key: str
    model: str


@dataclass(frozen=True)
class ChatOutcome:
    """One successful chat completion plus the provenance callers persist."""

    content: str
    model: str
    provider_alias: str
    attempts: int
    request_ids: tuple[str, ...]
    json_mode_requested: bool
    json_mode_sent: bool
    # True when the provider rejected a capability and the transport
    # retried once without it. Visible in attempt provenance.
    json_mode_dropped: bool
    reasoning_effort_dropped: bool


def get_llm_model() -> str:
    return os.environ.get("OPENAI_MODEL", DEFAULT_MODEL)


def get_video_prompt_model() -> str:
    return os.environ.get("VIDEO_PROMPT_MODEL", DEFAULT_MODEL)


def get_opponent_models() -> list[str]:
    """The models the Start game picker offers. Always includes the
    default; OPPONENT_MODELS prepends alternatives in its own order."""
    raw = os.environ.get("OPPONENT_MODELS", "")
    models = [entry.strip() for entry in raw.split(",") if entry.strip()]
    default = get_llm_model()
    if default not in models:
        models.append(default)
    return models


def is_llm_configured() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY"))


def opponent_settings(model: str | None = None) -> LlmSettings:
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise LlmNotConfiguredError("OPENAI_API_KEY is not set")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    return LlmSettings(
        profile="opponent", base_url=base_url, api_key=api_key, model=model or get_llm_model()
    )


def video_prompt_settings() -> LlmSettings:
    api_key = os.environ.get("VIDEO_PROMPT_API_KEY") or os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise LlmNotConfiguredError("VIDEO_PROMPT_API_KEY and OPENAI_API_KEY are not set")
    base_url = (
        os.environ.get("VIDEO_PROMPT_BASE_URL")
        or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    ).rstrip("/")
    return LlmSettings(
        profile="video_prompt", base_url=base_url, api_key=api_key, model=get_video_prompt_model()
    )


def chat(
    messages: list[dict],
    *,
    json_response: bool = False,
    timeout: float = MAX_TIMEOUT_SECONDS,
    model: str | None = None,
) -> ChatOutcome:
    """One Chat Completion through the opponent profile."""
    return _chat_completion(
        messages,
        settings=opponent_settings(model),
        json_response=json_response,
        timeout=timeout,
    )


def video_prompt_chat(
    messages: list[dict],
    *,
    json_response: bool = True,
    timeout: float = MAX_TIMEOUT_SECONDS,
) -> ChatOutcome:
    """One scene draft from Luna or an explicitly configured replacement."""
    return _chat_completion(
        messages,
        settings=video_prompt_settings(),
        json_response=json_response,
        timeout=timeout,
    )


def _chat_completion(
    messages: list[dict],
    *,
    settings: LlmSettings,
    json_response: bool,
    timeout: float,
) -> ChatOutcome:
    body = build_chat_body(settings.model, messages, json_response=json_response)
    json_mode_sent = "response_format" in body
    json_mode_dropped = False
    reasoning_effort_dropped = False
    request_ids: list[str] = []
    attempt = 0
    transient_retries = 0
    permission_retries = 0
    url = f"{settings.base_url}/chat/completions"
    # `timeout` is the caller's whole budget for this call, not a
    # per-HTTP-attempt allowance: every one of the up to
    # MAX_TRANSIENT_RETRIES + 1 attempts, and every backoff sleep
    # between them, draws down this one absolute deadline instead of
    # each restarting a fresh clock. That is what keeps a short
    # caller-supplied timeout short even when the transport itself
    # has to retry.
    deadline = time.monotonic() + min(timeout, MAX_TIMEOUT_SECONDS)

    with httpx.Client() as client:
        while True:
            attempt += 1
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise LlmRequestError(
                    f"deadline exceeded before attempt {attempt} to {url} "
                    f"({settings.profile}); request_ids={_format_ids(request_ids)}",
                    request_ids=tuple(request_ids),
                    transport_attempts=attempt,
                    json_mode_dropped=json_mode_dropped,
                    reasoning_effort_dropped=reasoning_effort_dropped,
                )
            try:
                response = client.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {settings.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=body,
                    timeout=remaining,
                )
            except httpx.HTTPError as exc:
                remaining = deadline - time.monotonic()
                if transient_retries >= MAX_TRANSIENT_RETRIES or remaining <= 0:
                    raise LlmRequestError(
                        f"could not reach {url} ({settings.profile}); attempt={attempt}; "
                        f"request_ids={_format_ids(request_ids)}; "
                        f"error={type(exc).__name__}: {exc}",
                        request_ids=tuple(request_ids),
                        transport_attempts=attempt,
                        json_mode_dropped=json_mode_dropped,
                        reasoning_effort_dropped=reasoning_effort_dropped,
                    ) from exc
                transient_retries += 1
                _sleep_backoff(transient_retries, deadline)
                continue

            request_id = response.headers.get("x-request-id")
            if request_id:
                request_ids.append(request_id)

            if response.status_code == 200:
                content = _extract_content(
                    response,
                    settings,
                    attempt,
                    request_ids,
                    json_mode_dropped=json_mode_dropped,
                    reasoning_effort_dropped=reasoning_effort_dropped,
                )
                _remember_working_credential(settings)
                return ChatOutcome(
                    content=content,
                    model=settings.model,
                    provider_alias=settings.profile,
                    attempts=attempt,
                    request_ids=tuple(request_ids),
                    json_mode_requested=json_response,
                    json_mode_sent=json_mode_sent,
                    json_mode_dropped=json_mode_dropped,
                    reasoning_effort_dropped=reasoning_effort_dropped,
                )

            if response.status_code == 400:
                message = _response_error_message(response)
                # The one allowed 400 fallback per capability: the
                # provider must name the exact field it rejected. Any
                # other 400 is a malformed request and fails loudly.
                if (
                    "response_format" in body
                    and not json_mode_dropped
                    and ("response_format" in message or "json_object" in message)
                ):
                    body.pop("response_format", None)
                    json_mode_dropped = True
                    continue
                if (
                    "reasoning_effort" in body
                    and not reasoning_effort_dropped
                    and "reasoning_effort" in message
                ):
                    body.pop("reasoning_effort", None)
                    reasoning_effort_dropped = True
                    continue
                raise _request_error(
                    response,
                    settings,
                    attempt,
                    request_ids,
                    json_mode_dropped=json_mode_dropped,
                    reasoning_effort_dropped=reasoning_effort_dropped,
                )

            if response.status_code == 401:
                remaining = deadline - time.monotonic()
                if (
                    _is_generic_permission_401(response)
                    and permission_retries < MAX_PERMISSION_RETRIES
                    and _transient_401_evidence(settings)
                    and remaining > 0
                ):
                    permission_retries += 1
                    _sleep_backoff(permission_retries, deadline)
                    continue
                raise _request_error(
                    response,
                    settings,
                    attempt,
                    request_ids,
                    json_mode_dropped=json_mode_dropped,
                    reasoning_effort_dropped=reasoning_effort_dropped,
                )

            if response.status_code == 429 or response.status_code >= 500:
                remaining = deadline - time.monotonic()
                if transient_retries >= MAX_TRANSIENT_RETRIES or remaining <= 0:
                    raise _request_error(
                        response,
                        settings,
                        attempt,
                        request_ids,
                        json_mode_dropped=json_mode_dropped,
                        reasoning_effort_dropped=reasoning_effort_dropped,
                    )
                transient_retries += 1
                _sleep_backoff(
                    transient_retries, deadline, retry_after=response.headers.get("retry-after")
                )
                continue

            # Any other status is deterministic; retrying cannot fix it.
            raise _request_error(
                response,
                settings,
                attempt,
                request_ids,
                json_mode_dropped=json_mode_dropped,
                reasoning_effort_dropped=reasoning_effort_dropped,
            )


def _extract_content(
    response: httpx.Response,
    settings: LlmSettings,
    attempt: int,
    request_ids: list[str],
    *,
    json_mode_dropped: bool = False,
    reasoning_effort_dropped: bool = False,
) -> str:
    """Validates the response shape before indexing into it. An empty
    string is a valid shape; classifying it is the caller's decision."""
    try:
        data = response.json()
    except ValueError as exc:
        raise LlmRequestError(
            f"non-JSON 200 body from {settings.profile}; attempt={attempt}; "
            f"request_ids={_format_ids(request_ids)}; body={response.text[:ERROR_EXCERPT_CHARS]}",
            status_code=200,
            request_ids=tuple(request_ids),
            transport_attempts=attempt,
            json_mode_dropped=json_mode_dropped,
            reasoning_effort_dropped=reasoning_effort_dropped,
        ) from exc
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LlmRequestError(
            f"unexpected llm response shape from {settings.profile}; attempt={attempt}; "
            f"request_ids={_format_ids(request_ids)}; body={str(data)[:ERROR_EXCERPT_CHARS]}",
            status_code=200,
            request_ids=tuple(request_ids),
            transport_attempts=attempt,
            json_mode_dropped=json_mode_dropped,
            reasoning_effort_dropped=reasoning_effort_dropped,
        ) from exc
    if content is None:
        return ""
    if not isinstance(content, str):
        raise LlmRequestError(
            f"llm content is {type(content).__name__}, not text; attempt={attempt}; "
            f"request_ids={_format_ids(request_ids)}",
            status_code=200,
            request_ids=tuple(request_ids),
            transport_attempts=attempt,
            json_mode_dropped=json_mode_dropped,
            reasoning_effort_dropped=reasoning_effort_dropped,
        )
    return content


def _request_error(
    response: httpx.Response,
    settings: LlmSettings,
    attempt: int,
    request_ids: list[str],
    *,
    json_mode_dropped: bool = False,
    reasoning_effort_dropped: bool = False,
) -> LlmRequestError:
    """Status, attempt, request ids, and a bounded excerpt. Never the
    API key, never the prompt."""
    return LlmRequestError(
        f"{response.status_code} from {settings.profile} {response.request.url}; "
        f"attempt={attempt}; request_ids={_format_ids(request_ids)}; "
        f"body={response.text[:ERROR_EXCERPT_CHARS]}",
        status_code=response.status_code,
        request_ids=tuple(request_ids),
        transport_attempts=attempt,
        json_mode_dropped=json_mode_dropped,
        reasoning_effort_dropped=reasoning_effort_dropped,
    )


def _format_ids(request_ids: list[str]) -> str:
    return str(request_ids or ["missing"])


def _is_generic_permission_401(response: httpx.Response) -> bool:
    return _response_error_message(response).rstrip(".") == TRANSIENT_PERMISSION_ERROR


def _transient_401_evidence(settings: LlmSettings) -> bool:
    """The generic-permissions 401 retries only on evidence: the same
    credential already worked in this process, or the operator opted in
    after creating or rotating a key. Never inferred from the response."""
    if _credential_fingerprint(settings) in _working_credentials:
        return True
    return os.environ.get("OPENAI_RECENT_KEY_401_RETRY") == "1"


def _credential_fingerprint(settings: LlmSettings) -> str:
    raw = f"{settings.base_url}|{settings.api_key}".encode()
    return hashlib.sha256(raw).hexdigest()


def _remember_working_credential(settings: LlmSettings) -> None:
    _working_credentials.add(_credential_fingerprint(settings))


def reset_credential_memory() -> None:
    """Test hook: forget which credentials have succeeded in-process."""
    _working_credentials.clear()


def _response_error_message(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text.strip()
    if not isinstance(payload, dict):
        return response.text.strip()
    error = payload.get("error")
    if isinstance(error, dict) and isinstance(error.get("message"), str):
        return error["message"].strip()
    if isinstance(payload.get("message"), str):
        return payload["message"].strip()
    return response.text.strip()


def _sleep_backoff(retry_number: int, deadline: float, retry_after: str | None = None) -> None:
    """Sleeps for the backoff duration, capped to whatever remains of
    the call's absolute deadline. Without the cap, a retry's own wait
    could by itself carry a call past the budget the caller asked
    for -- the same overrun this deadline exists to prevent."""
    duration = _backoff_duration(retry_number, retry_after)
    remaining = deadline - time.monotonic()
    time.sleep(max(0.0, min(duration, remaining)))


def _backoff_duration(retry_number: int, retry_after: str | None) -> float:
    if retry_after is not None:
        try:
            return min(float(retry_after), RETRY_AFTER_CAP_SECONDS)
        except ValueError:
            pass
    return (2 ** (retry_number - 1)) + random.uniform(0, 0.25)
