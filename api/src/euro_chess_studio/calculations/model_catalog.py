"""Typed model capability catalog and request-body construction.

Capability decisions live here, in one pure calculation, instead of
scattered string checks in the transport. The catalog covers the two
models the workshop actually runs: local Gemma through llama.cpp and
hosted Luna. An unknown OpenAI-compatible model gets the conservative
profile: no `reasoning_effort`, JSON mode allowed (the transport still
has a narrow one-shot fallback if the provider rejects it).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelCapabilities:
    supports_reasoning_effort: bool
    supports_json_response_format: bool


# llama.cpp's OpenAI-compatible server rejects reasoning_effort but
# enforces response_format={"type": "json_object"} through its grammar
# sampler. Both Gemma spellings appear in configs: the API alias that
# `just start-gemma` serves and the full GGUF repository id.
_CATALOG: dict[str, ModelCapabilities] = {
    "gpt-5.6-luna": ModelCapabilities(
        supports_reasoning_effort=True, supports_json_response_format=True
    ),
    "gemma-4-2b-local": ModelCapabilities(
        supports_reasoning_effort=False, supports_json_response_format=True
    ),
    "google/gemma-4-E2B-it-qat-q4_0-gguf": ModelCapabilities(
        supports_reasoning_effort=False, supports_json_response_format=True
    ),
}

DEFAULT_CAPABILITIES = ModelCapabilities(
    supports_reasoning_effort=False, supports_json_response_format=True
)


def capabilities_for(model: str) -> ModelCapabilities:
    return _CATALOG.get(model, DEFAULT_CAPABILITIES)


def build_chat_body(model: str, messages: list[dict], *, json_response: bool) -> dict:
    """The Chat Completions request body this model can actually accept."""
    capabilities = capabilities_for(model)
    body: dict = {"model": model, "messages": messages}
    if capabilities.supports_reasoning_effort:
        body["reasoning_effort"] = "medium"
    if json_response and capabilities.supports_json_response_format:
        body["response_format"] = {"type": "json_object"}
    return body
