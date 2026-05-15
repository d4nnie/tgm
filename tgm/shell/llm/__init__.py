import os
from collections.abc import Mapping

from tgm.core.types import LlmProviderConfig
from tgm.shell.llm.openaicompat import OpenAiCompatibleProvider


def build_provider(
    config: LlmProviderConfig,
    env: Mapping[str, str] | None = None,
) -> OpenAiCompatibleProvider:
    return OpenAiCompatibleProvider(
        base_url=config.base_url,
        api_key=_resolve_api_key(config.api_key_env, env or os.environ),
        model=config.model,
        options=config.options,
    )


def _resolve_api_key(api_key_env: str | None, env: Mapping[str, str]) -> str | None:
    if not api_key_env:
        return None
    return env.get(api_key_env)
