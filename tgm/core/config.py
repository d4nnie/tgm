from collections.abc import Mapping, Sequence
from typing import Any, cast, get_args
from urllib.parse import SplitResult, urlsplit

from tgm.core.types import LlmProvider, LlmProviderConfig, TelegramCredentials

_VALID_LLM_PROVIDERS: frozenset[str] = frozenset(get_args(LlmProvider))
_LOOPBACK_HOSTNAMES: frozenset[str] = frozenset({"127.0.0.1", "localhost", "::1"})

DEFAULT_LLM_CONFIG_SECTION: dict[str, Any] = {
    "provider": "openai-compat",
    "base_url": "http://127.0.0.1:11434/v1",
    "model": "gpt-oss:20b",
    "options": {"num_ctx": 24576},
}


def extract_telegram_credentials_from_env(env: Mapping[str, str]) -> TelegramCredentials | None:
    api_id = env.get("TGM_API_ID")
    api_hash = env.get("TGM_API_HASH")
    if not (api_id and api_hash):
        return None
    parsed_api_id = _parse_api_id(api_id, source="TGM_API_ID")
    return TelegramCredentials(api_id=parsed_api_id, api_hash=api_hash, phone=None)


def extract_telegram_credentials_from_config(config: Mapping[str, Any]) -> TelegramCredentials | None:
    telegram_section = config.get("telegram") or {}
    if "api_id" not in telegram_section or "api_hash" not in telegram_section:
        return None
    return TelegramCredentials(
        api_id=_parse_api_id(telegram_section["api_id"], source="telegram.api_id"),
        api_hash=str(telegram_section["api_hash"]),
        phone=telegram_section.get("phone"),
    )


def _parse_api_id(raw_value: object, *, source: str) -> int:
    if isinstance(raw_value, int) and not isinstance(raw_value, bool):
        return raw_value
    if isinstance(raw_value, str):
        try:
            return int(raw_value)
        except ValueError as error:
            raise ValueError(f"{source} must be a positive integer; got {raw_value!r}") from error
    raise ValueError(f"{source} must be a positive integer; got {raw_value!r}")


def merge_telegram_credentials(config: Mapping[str, Any], credentials: TelegramCredentials) -> dict[str, Any]:  # noqa: WPS221  # parameterised-type signature
    new_config = dict(config)
    telegram_section = dict(new_config.get("telegram") or {})
    telegram_section["api_id"] = credentials.api_id
    telegram_section["api_hash"] = credentials.api_hash
    if credentials.phone is not None:
        telegram_section["phone"] = credentials.phone
    new_config["telegram"] = telegram_section
    return new_config


def merge_telegram_phone(config: Mapping[str, Any], phone: str) -> dict[str, Any]:  # noqa: WPS221  # parameterised-type signature
    new_config = dict(config)
    telegram_section = dict(new_config.get("telegram") or {})
    telegram_section["phone"] = phone
    new_config["telegram"] = telegram_section
    return new_config


def extract_llm_provider_config_from_config(config: Mapping[str, Any]) -> LlmProviderConfig:
    section = _require_llm_section(config)
    provider_config = LlmProviderConfig(
        provider=_extract_llm_provider(section),
        base_url=_extract_required_string(section, "base_url"),
        model=_extract_required_string(section, "model"),
        api_key_env=_extract_optional_string(section, "api_key_env"),
        options=_extract_optional_mapping(section, "options"),
        allow_hosts=_extract_allow_hosts(section),
    )
    validate_base_url(provider_config.base_url, provider_config.allow_hosts)
    return provider_config


def validate_base_url(base_url: str, allow_hosts: Sequence[str]) -> None:
    parsed = _parse_base_url(base_url)
    hostname = parsed.hostname
    if not hostname:
        raise ValueError(f"llm.base_url {base_url!r} has no hostname")
    if hostname in _LOOPBACK_HOSTNAMES:
        return
    _require_https_remote(base_url, parsed.scheme)
    _require_allowed_host(base_url, hostname, allow_hosts)


def _parse_base_url(base_url: str) -> SplitResult:
    if not base_url:
        raise ValueError("llm.base_url must be a non-empty URL")
    parsed = urlsplit(base_url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError(f"llm.base_url {base_url!r} must use http or https scheme")
    return parsed


def _require_https_remote(base_url: str, scheme: str) -> None:
    if scheme != "https":
        raise ValueError(f"llm.base_url {base_url!r} non-loopback host requires https")


def _require_allowed_host(base_url: str, hostname: str, allow_hosts: Sequence[str]) -> None:
    if hostname not in allow_hosts:
        raise ValueError(f"llm.base_url {base_url!r} is not in the allow-list (loopback + llm.allow_hosts)")


def _require_llm_section(config: Mapping[str, Any]) -> Mapping[str, Any]:
    section = config.get("llm")
    if not isinstance(section, Mapping):
        raise ValueError("Missing [llm] section in config")
    return section


def _extract_llm_provider(section: Mapping[str, Any]) -> LlmProvider:
    value = section.get("provider")
    if value == "anthropic":
        raise ValueError("Provider 'anthropic' is reserved for a future release")
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


def _extract_optional_mapping(section: Mapping[str, Any], field_name: str) -> dict[str, Any] | None:  # noqa: WPS221  # parameterised-type signature
    value = section.get(field_name)
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise ValueError(f"llm.{field_name} must be a table")
    return dict(value)


def _extract_allow_hosts(section: Mapping[str, Any]) -> tuple[str, ...]:
    value = section.get("allow_hosts")
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ValueError("llm.allow_hosts must be a list of hostnames")
    for entry in value:
        if not isinstance(entry, str) or not entry:
            raise ValueError("llm.allow_hosts entries must be non-empty strings")
    return tuple(value)
