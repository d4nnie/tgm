import logging
import os
import tomllib
from pathlib import Path
from typing import Any

import tomli_w

from tgm.core.config import (
    DEFAULT_LLM_CONFIG_SECTION,
    extract_llm_provider_config_from_config,
    extract_telegram_credentials_from_config,
    extract_telegram_credentials_from_env,
    merge_telegram_credentials,
    merge_telegram_phone,
)
from tgm.core.types import LlmProviderConfig, TelegramCredentials
from tgm.shell.platform import get_user_data_dir

logger = logging.getLogger(__name__)

_CONFIG_FILENAME = "config.toml"


def resolve_config_path() -> Path:
    return get_user_data_dir() / _CONFIG_FILENAME


def load_telegram_credentials() -> TelegramCredentials | None:
    from_env = extract_telegram_credentials_from_env(os.environ)
    if from_env is not None:
        return from_env
    return extract_telegram_credentials_from_config(_read_config())


def save_telegram_credentials(credentials: TelegramCredentials) -> None:
    new_config = merge_telegram_credentials(_read_config(), credentials)
    _write_config_atomic(new_config)
    logger.info("Saved Telegram credentials to config")


def save_telegram_phone(phone: str) -> None:
    new_config = merge_telegram_phone(_read_config(), phone)
    _write_config_atomic(new_config)
    logger.info("Saved Telegram phone to config")


def load_llm_provider_config() -> LlmProviderConfig:
    config = _read_config()
    if "llm" not in config:
        config = _ensure_default_llm_section(config)
    return extract_llm_provider_config_from_config(config)


def _ensure_default_llm_section(config: dict[str, Any]) -> dict[str, Any]:
    new_config = dict(config)
    new_config["llm"] = dict(DEFAULT_LLM_CONFIG_SECTION)
    _write_config_atomic(new_config)
    logger.info("Wrote default [llm] section to config")
    return new_config


def _read_config() -> dict[str, Any]:
    path = resolve_config_path()
    if not path.exists() or path.stat().st_size == 0:
        return {}
    with open(path, "rb") as file:
        return tomllib.load(file)


def _write_config_atomic(config: dict[str, Any]) -> None:
    path = resolve_config_path()
    temp_path = path.parent / f"{path.name}.tmp"
    with open(temp_path, "wb") as file:
        tomli_w.dump(config, file)
    # On Windows os.chmod is a no-op for 0o600; final permission is healed by
    # restrict_path_access on next ensure_user_data_dir.
    os.chmod(temp_path, 0o600)
    os.replace(temp_path, path)
