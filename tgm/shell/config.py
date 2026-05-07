import os
import tomllib
from pathlib import Path
from typing import Any

import tomli_w

from tgm.core.types import TelegramCreds
from tgm.shell.platform import user_data_dir

_CONFIG_FILENAME = "config.toml"


def config_path() -> Path:
    return user_data_dir() / _CONFIG_FILENAME


def load_telegram_creds() -> TelegramCreds | None:
    env_api_id = os.environ.get("TGM_API_ID")
    env_api_hash = os.environ.get("TGM_API_HASH")
    if env_api_id and env_api_hash:
        return TelegramCreds(api_id=int(env_api_id), api_hash=env_api_hash, phone=None)

    config = _read_config()
    telegram_section = config.get("telegram") or {}
    if "api_id" in telegram_section and "api_hash" in telegram_section:
        return TelegramCreds(
            api_id=int(telegram_section["api_id"]),
            api_hash=str(telegram_section["api_hash"]),
            phone=telegram_section.get("phone"),
        )

    return None


def save_telegram_creds(creds: TelegramCreds) -> None:
    config = _read_config()
    telegram_section = config.setdefault("telegram", {})
    telegram_section["api_id"] = creds.api_id
    telegram_section["api_hash"] = creds.api_hash
    if creds.phone:
        telegram_section["phone"] = creds.phone
    _write_config_atomic(config)


def save_telegram_phone(phone: str) -> None:
    config = _read_config()
    telegram_section = config.setdefault("telegram", {})
    telegram_section["phone"] = phone
    _write_config_atomic(config)


def _read_config() -> dict[str, Any]:
    path = config_path()
    if not path.exists() or path.stat().st_size == 0:
        return {}
    with open(path, "rb") as file:
        return tomllib.load(file)


def _write_config_atomic(config: dict[str, Any]) -> None:
    path = config_path()
    temp_path = path.parent / f"{path.name}.tmp"
    with open(temp_path, "wb") as file:
        tomli_w.dump(config, file)
    os.replace(temp_path, path)
