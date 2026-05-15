import contextlib
import functools
import getpass
import logging
import os
import subprocess
import sys
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import ParamSpec, TypeVar

import click
import platformdirs

from tgm.core.errors import SingleInstanceError

logger = logging.getLogger(__name__)

_APP_NAME = "telegram-monitor"
_CONFIG_FILENAME = "config.toml"

_SingleInstanceParams = ParamSpec("_SingleInstanceParams")
_SingleInstanceReturn = TypeVar("_SingleInstanceReturn")


def get_user_data_dir() -> Path:
    return Path(platformdirs.user_data_dir(_APP_NAME, appauthor=False, roaming=True))


def ensure_user_data_dir() -> Path:
    directory = get_user_data_dir()
    directory.mkdir(parents=True, exist_ok=True)
    restrict_path_access(directory)

    config_path = directory / _CONFIG_FILENAME
    if not config_path.exists():
        config_path.touch()

    return directory


def restrict_path_access(path: Path) -> None:
    """Restrict path access to the current user only.

    POSIX: chmod 0700 for directories, 0600 for files.
    Windows: icacls with broken inheritance, granting full control to the current user.
    """
    if sys.platform == "win32":
        _restrict_path_access_windows(path)
    else:
        path.chmod(0o700 if path.is_dir() else 0o600)


@contextlib.contextmanager
def acquire_exclusive_lock(name: str) -> Iterator[None]:
    if sys.platform == "win32":
        with _acquire_windows_mutex(name):
            yield
    else:
        with _acquire_posix_flock(name):
            yield


def require_single_instance(
    function: Callable[_SingleInstanceParams, _SingleInstanceReturn],
) -> Callable[_SingleInstanceParams, _SingleInstanceReturn]:
    @functools.wraps(function)
    def wrapper(*args: _SingleInstanceParams.args, **kwargs: _SingleInstanceParams.kwargs) -> _SingleInstanceReturn:
        try:
            with acquire_exclusive_lock("single-instance"):
                return function(*args, **kwargs)
        except SingleInstanceError as error:
            raise click.ClickException(str(error)) from error

    return wrapper


def _restrict_path_access_windows(path: Path) -> None:
    username = getpass.getuser()
    ace = f"{username}:(OI)(CI)F" if path.is_dir() else f"{username}:F"
    subprocess.run(
        ["icacls", str(path), "/inheritance:r", "/grant:r", ace],
        check=True,
        capture_output=True,
    )


@contextlib.contextmanager
def _acquire_posix_flock(name: str) -> Iterator[None]:
    import fcntl

    lock_path = _resolve_posix_lock_path(name)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.touch(exist_ok=True)

    with open(lock_path, "r+") as lock_file:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            logger.error("Another instance is already running", extra={"lock_path": str(lock_path)})
            raise SingleInstanceError(f"Another instance is already running (lock file: {lock_path})") from error

        lock_file.seek(0)
        lock_file.truncate()
        lock_file.write(str(os.getpid()))
        lock_file.flush()

        logger.info("Acquired exclusive lock", extra={"lock_path": str(lock_path)})
        yield


def _resolve_posix_lock_path(name: str) -> Path:
    lock_filename = f"{_APP_NAME}.{name}.pid"
    runtime_directory = os.environ.get("XDG_RUNTIME_DIR")
    if runtime_directory:
        return Path(runtime_directory) / lock_filename
    return get_user_data_dir() / lock_filename


@contextlib.contextmanager
def _acquire_windows_mutex(name: str) -> Iterator[None]:
    import ctypes
    from ctypes import wintypes

    error_already_exists = 183
    mutex_name = f"{_APP_NAME}-{name}"

    kernel32 = ctypes.windll.kernel32  # ty: ignore[unresolved-attribute]
    kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
    kernel32.CreateMutexW.restype = wintypes.HANDLE
    kernel32.ReleaseMutex.argtypes = [wintypes.HANDLE]
    kernel32.ReleaseMutex.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL

    mutex_handle = kernel32.CreateMutexW(None, True, mutex_name)
    last_error = ctypes.GetLastError()  # ty: ignore[unresolved-attribute]

    if not mutex_handle or last_error == error_already_exists:
        if mutex_handle:
            kernel32.CloseHandle(mutex_handle)
        logger.error("Another instance is already running", extra={"mutex": mutex_name})
        raise SingleInstanceError(f"Another instance is already running (Windows mutex: {mutex_name})")

    logger.info("Acquired exclusive lock", extra={"mutex": mutex_name})
    try:
        yield
    finally:
        kernel32.ReleaseMutex(mutex_handle)
        kernel32.CloseHandle(mutex_handle)
