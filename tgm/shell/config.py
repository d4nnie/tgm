import logging
import os
import tomllib
from pathlib import Path
from typing import Any

import tomli_w

from tgm.core.config import (
    extract_telegram_credentials_from_config,
    extract_telegram_credentials_from_env,
    merge_telegram_credentials,
    merge_telegram_phone,
)
from tgm.core.types import TelegramCredentials
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
    os.replace(temp_path, path)
