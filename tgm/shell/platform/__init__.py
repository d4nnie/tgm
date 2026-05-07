import getpass
import subprocess
import sys
from pathlib import Path

import platformdirs

_APP_NAME = "telegram-monitor"
_CONFIG_FILENAME = "config.toml"


def user_data_dir() -> Path:
    return Path(platformdirs.user_data_dir(_APP_NAME, appauthor=False, roaming=True))


def ensure_user_data_dir() -> Path:
    directory = user_data_dir()
    directory.mkdir(parents=True, exist_ok=True)
    _restrict_directory_access(directory)

    config_path = directory / _CONFIG_FILENAME
    if not config_path.exists():
        config_path.touch()

    return directory


def _restrict_directory_access(directory: Path) -> None:
    if sys.platform == "win32":
        _restrict_directory_access_windows(directory)
    else:
        directory.chmod(0o700)


def _restrict_directory_access_windows(directory: Path) -> None:
    username = getpass.getuser()
    subprocess.run(
        ["icacls", str(directory), "/inheritance:r", "/grant:r", f"{username}:(OI)(CI)F"],
        check=True,
        capture_output=True,
    )
