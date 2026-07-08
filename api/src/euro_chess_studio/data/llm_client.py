"""OpenAI-compatible chat completions client. No business logic here.

Configured entirely through the environment so the presenter can point
it at api.openai.com today and any compatible endpoint (OpenRouter,
Hugging Face router, vLLM, llama.cpp) later without touching code:

    OPENAI_API_KEY    required
    OPENAI_BASE_URL   default https://api.openai.com/v1
    OPENAI_MODEL      default gpt-5.5-mini; analysis and the default opponent
    OPPONENT_MODELS   optional comma-separated list of extra opponents
                      to offer in the Start game picker, e.g.
                      google/gemma-4-2b-it,openai/gpt-5.5
"""

import os

import httpx


class LlmNotConfiguredError(RuntimeError):
    pass


class LlmRequestError(RuntimeError):
    pass


def get_llm_model() -> str:
    return os.environ.get("OPENAI_MODEL", "gpt-5.5-mini")


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


def chat(
    messages: list[dict],
    *,
    json_response: bool = False,
    timeout: float = 60.0,
    model: str | None = None,
) -> str:
    """One chat completion, returning the assistant text. When
    json_response is set, asks for JSON mode and quietly retries without
    it for endpoints that reject the parameter."""
    base_url, api_key, model = _settings(model)
    body: dict = {"model": model, "messages": messages}
    if json_response:
        body["response_format"] = {"type": "json_object"}

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json=body,
            )
            if response.status_code == 400 and json_response:
                body.pop("response_format", None)
                response = client.post(
                    f"{base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json=body,
                )
            if response.status_code != 200:
                raise LlmRequestError(
                    f"llm endpoint returned {response.status_code}: {response.text[:300]}"
                )
            data = response.json()
    except httpx.HTTPError as exc:
        # Unreachable host, timeout, TLS trouble: a clean model error the
        # UI can display, not an anonymous 500.
        raise LlmRequestError(f"could not reach {base_url}: {exc}") from exc

    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LlmRequestError(f"unexpected llm response shape: {str(data)[:300]}") from exc
    if not isinstance(content, str) or not content.strip():
        raise LlmRequestError("llm returned empty content")
    return content
