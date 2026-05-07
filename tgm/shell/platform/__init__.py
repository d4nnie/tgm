from pathlib import Path

import platformdirs

_APP_NAME = "telegram-monitor"


def user_data_dir() -> Path:
    return Path(platformdirs.user_data_dir(_APP_NAME, appauthor=False, roaming=True))
