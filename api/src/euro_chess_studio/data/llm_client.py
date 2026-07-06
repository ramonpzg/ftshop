"""OpenAI-compatible chat completions client. No business logic here.

Configured entirely through the environment so the presenter can point
it at api.openai.com today and any compatible endpoint (Hugging Face
router, vLLM, llama.cpp) later without touching code:

    OPENAI_API_KEY   required
    OPENAI_BASE_URL  default https://api.openai.com/v1
    OPENAI_MODEL     default gpt-5.5-mini
"""

import os

import httpx


class LlmNotConfiguredError(RuntimeError):
    pass


class LlmRequestError(RuntimeError):
    pass


def get_llm_model() -> str:
    return os.environ.get("OPENAI_MODEL", "gpt-5.5-mini")


def is_llm_configured() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY"))


def _settings() -> tuple[str, str, str]:
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise LlmNotConfiguredError("OPENAI_API_KEY is not set")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    return base_url, api_key, get_llm_model()


def chat(messages: list[dict], *, json_response: bool = False, timeout: float = 60.0) -> str:
    """One chat completion, returning the assistant text. When
    json_response is set, asks for JSON mode and quietly retries without
    it for endpoints that reject the parameter."""
    base_url, api_key, model = _settings()
    body: dict = {"model": model, "messages": messages}
    if json_response:
        body["response_format"] = {"type": "json_object"}

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
            raise LlmRequestError(f"llm endpoint returned {response.status_code}: {response.text[:300]}")
        data = response.json()

    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LlmRequestError(f"unexpected llm response shape: {str(data)[:300]}") from exc
    if not isinstance(content, str) or not content.strip():
        raise LlmRequestError("llm returned empty content")
    return content
