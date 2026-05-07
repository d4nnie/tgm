from collections.abc import Mapping
from typing import Any

from tgm.core.types import TelegramCredentials


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
