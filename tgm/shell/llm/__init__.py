import os
from collections.abc import Mapping
from typing import Any, Protocol

from tgm.core.llm import JsonSchema, LLMUnavailableError
from tgm.core.types import LlmProviderConfig
from tgm.shell.llm.openaicompat import OpenAiCompatibleProvider


class LlmProvider(Protocol):
    async def call_json(
        self,
        system: str,
        user: str,
        schema: JsonSchema,
        max_input_tokens: int,
    ) -> dict[str, Any]: ...

    async def aclose(self) -> None: ...


class LlmApiKeyMissingError(ValueError):
    pass


def build_provider(
    config: LlmProviderConfig,
    env: Mapping[str, str] | None = None,
) -> LlmProvider:
    api_key = _resolve_api_key(config.api_key_env, env or os.environ)
    if config.api_key_env and not api_key:
        raise LlmApiKeyMissingError(
            f"LLM api_key_env={config.api_key_env!r} is configured but the env var is unset or empty; "
            "export the key or unset llm.api_key_env"
        )
    return OpenAiCompatibleProvider(
        base_url=config.base_url,
        api_key=api_key,
        model=config.model,
        options=config.options,
    )


def _resolve_api_key(api_key_env: str | None, env: Mapping[str, str]) -> str | None:  # noqa: WPS221  # parameterised-type signature
    if not api_key_env:
        return None
    value = env.get(api_key_env)
    return value if value else None


__all__ = ["LlmApiKeyMissingError", "LlmProvider", "LLMUnavailableError", "build_provider"]
