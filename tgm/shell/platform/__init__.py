from pathlib import Path

import platformdirs

_APP_NAME = "telegram-monitor"
_CONFIG_FILENAME = "config.toml"


def user_data_dir() -> Path:
    return Path(platformdirs.user_data_dir(_APP_NAME, appauthor=False, roaming=True))


def ensure_user_data_dir() -> Path:
    directory = user_data_dir()
    directory.mkdir(parents=True, exist_ok=True)

    config_path = directory / _CONFIG_FILENAME
    if not config_path.exists():
        config_path.touch()

    return directory
