"""OpenAI-compatible chat completions client. No business logic here.

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
"""

import os
import random
import time

import httpx

DEFAULT_MODEL = "gpt-5.6-luna"
TRANSIENT_PERMISSION_ERROR = "You have insufficient permissions for this operation"


class LlmNotConfiguredError(RuntimeError):
    pass


class LlmRequestError(RuntimeError):
    pass


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


def _settings(model: str | None = None) -> tuple[str, str, str]:
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise LlmNotConfiguredError("OPENAI_API_KEY is not set")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    return base_url, api_key, model or get_llm_model()


def _video_prompt_settings() -> tuple[str, str, str]:
    api_key = os.environ.get("VIDEO_PROMPT_API_KEY") or os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise LlmNotConfiguredError("VIDEO_PROMPT_API_KEY and OPENAI_API_KEY are not set")
    base_url = (
        os.environ.get("VIDEO_PROMPT_BASE_URL")
        or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    ).rstrip("/")
    return base_url, api_key, get_video_prompt_model()


def chat(
    messages: list[dict],
    *,
    json_response: bool = False,
    timeout: float = 120.0,
    model: str | None = None,
) -> str:
    """One Chat Completion, returning the assistant text.

    JSON mode falls back once for compatible endpoints that reject
    response_format. Retries cover rate limits, server failures, transport
    failures, and the generic permissions 401 observed while a new project key
    was propagating. Explicit credential failures are not retried.
    """
    return _chat_completion(
        messages,
        settings=_settings(model),
        json_response=json_response,
        timeout=timeout,
    )


def video_prompt_chat(
    messages: list[dict],
    *,
    json_response: bool = True,
    timeout: float = 120.0,
) -> str:
    """One video-scene draft from Luna or an explicitly configured replacement."""
    return _chat_completion(
        messages,
        settings=_video_prompt_settings(),
        json_response=json_response,
        timeout=timeout,
    )


def _chat_completion(
    messages: list[dict],
    *,
    settings: tuple[str, str, str],
    json_response: bool,
    timeout: float,
) -> str:
    base_url, api_key, model = settings
    body: dict = {
        "model": model,
        "reasoning_effort": "medium",
        "messages": messages,
    }
    if json_response:
        body["response_format"] = {"type": "json_object"}

    request_ids: list[str] = []
    with httpx.Client(timeout=timeout) as client:
        for attempt in range(3):
            try:
                response = client.post(
                    f"{base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json=body,
                )
            except httpx.HTTPError as exc:
                if attempt == 2:
                    raise LlmRequestError(
                        f"could not reach {base_url}; attempt={attempt + 1}; error={exc}"
                    ) from exc
                _sleep_before_retry(attempt)
                continue

            if response.status_code == 400 and "response_format" in body:
                body.pop("response_format", None)
                continue

            if response.status_code == 200:
                data = response.json()
                break

            request_id = response.headers.get("x-request-id")
            if request_id:
                request_ids.append(request_id)

            if not _is_retryable(response) or attempt == 2:
                raise LlmRequestError(
                    f"{response.status_code} from {response.request.url}; "
                    f"attempt={attempt + 1}; request_ids={request_ids or ['missing']}; "
                    f"body={response.text[:400]}"
                )

            _sleep_before_retry(attempt)
        else:  # pragma: no cover - the loop either breaks or raises
            raise LlmRequestError("chat completion retry loop ended unexpectedly")

    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LlmRequestError(f"unexpected llm response shape: {str(data)[:300]}") from exc
    if not isinstance(content, str) or not content.strip():
        raise LlmRequestError("llm returned empty content")
    return content


def _is_retryable(response: httpx.Response) -> bool:
    if response.status_code == 429 or response.status_code >= 500:
        return True
    if response.status_code != 401:
        return False
    return _response_error_message(response).rstrip(".") == TRANSIENT_PERMISSION_ERROR


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


def _sleep_before_retry(attempt: int) -> None:
    time.sleep((2**attempt) + random.uniform(0, 0.25))
