from collections.abc import Mapping
from typing import Any, cast, get_args

from tgm.core.types import LlmProvider, LlmProviderConfig, TelegramCredentials

_VALID_LLM_PROVIDERS: frozenset[str] = frozenset(get_args(LlmProvider))

DEFAULT_LLM_CONFIG_SECTION: dict[str, Any] = {
    "provider": "openai-compat",
    "base_url": "http://127.0.0.1:11434/v1",
    "model": "gpt-oss:20b",
    "options": {"num_ctx": 24576},
}


def extract_telegram_credentials_from_env(env: Mapping[str, str]) -> TelegramCredentials | None:
    api_id = env.get("TGM_API_ID")
    api_hash = env.get("TGM_API_HASH")

    if api_id and api_hash:
        return TelegramCredentials(api_id=int(api_id), api_hash=api_hash, phone=None)
    return None


def extract_telegram_credentials_from_config(config: Mapping[str, Any]) -> TelegramCredentials | None:
    telegram_section = config.get("telegram") or {}
    if "api_id" in telegram_section and "api_hash" in telegram_section:
        return TelegramCredentials(
            api_id=int(telegram_section["api_id"]),
            api_hash=str(telegram_section["api_hash"]),
            phone=telegram_section.get("phone"),
        )
    return None


def merge_telegram_credentials(config: Mapping[str, Any], credentials: TelegramCredentials) -> dict[str, Any]:
    new_config = dict(config)
    telegram_section = dict(new_config.get("telegram") or {})
    telegram_section["api_id"] = credentials.api_id
    telegram_section["api_hash"] = credentials.api_hash

    if credentials.phone:
        telegram_section["phone"] = credentials.phone

    new_config["telegram"] = telegram_section
    return new_config


def merge_telegram_phone(config: Mapping[str, Any], phone: str) -> dict[str, Any]:
    new_config = dict(config)
    telegram_section = dict(new_config.get("telegram") or {})
    telegram_section["phone"] = phone
    new_config["telegram"] = telegram_section
    return new_config


def extract_llm_provider_config_from_config(config: Mapping[str, Any]) -> LlmProviderConfig:
    section = _require_llm_section(config)
    return LlmProviderConfig(
        provider=_extract_llm_provider(section),
        base_url=_extract_required_string(section, "base_url"),
        model=_extract_required_string(section, "model"),
        api_key_env=_extract_optional_string(section, "api_key_env"),
        options=_extract_optional_mapping(section, "options"),
    )


def _require_llm_section(config: Mapping[str, Any]) -> Mapping[str, Any]:
    section = config.get("llm")
    if not isinstance(section, Mapping):
        raise ValueError("Missing [llm] section in config")
    return section


def _extract_llm_provider(section: Mapping[str, Any]) -> LlmProvider:
    value = section.get("provider")
    if value not in _VALID_LLM_PROVIDERS:
        raise ValueError(f"llm.provider must be one of {sorted(_VALID_LLM_PROVIDERS)}; got: {value!r}")
    return cast(LlmProvider, value)


def _extract_required_string(section: Mapping[str, Any], field_name: str) -> str:
    value = section.get(field_name)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Missing or empty llm.{field_name}")
    return value


def _extract_optional_string(section: Mapping[str, Any], field_name: str) -> str | None:
    value = section.get(field_name)
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        raise ValueError(f"llm.{field_name} must be a string")
    return value


def _extract_optional_mapping(section: Mapping[str, Any], field_name: str) -> dict[str, Any] | None:
    value = section.get(field_name)
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise ValueError(f"llm.{field_name} must be a table")
    return dict(value)
