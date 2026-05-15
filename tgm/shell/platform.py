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


def resolve_config_path() -> Path:
    return get_user_data_dir() / _CONFIG_FILENAME


def ensure_user_data_dir() -> Path:
    directory = get_user_data_dir()
    directory.mkdir(parents=True, exist_ok=True)
    restrict_path_access(directory)

    config_path = directory / _CONFIG_FILENAME
    if not config_path.exists():
        config_path.touch()
    restrict_path_access(config_path)

    for session_path in directory.glob("session*"):
        if session_path.is_file():
            restrict_path_access(session_path)
    return directory


def restrict_path_access(path: Path) -> None:
    # POSIX: chmod 0700 for directories, 0600 for files.
    # Windows: icacls with broken inheritance, full control to current user.
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
        _try_flock(lock_file, lock_path, fcntl)
        _write_pid_to_lock(lock_file)
        logger.info("Acquired exclusive lock", extra={"lock_path": str(lock_path)})
        yield


def _try_flock(lock_file: object, lock_path: Path, fcntl_module: object) -> None:
    try:
        fcntl_module.flock(lock_file.fileno(), fcntl_module.LOCK_EX | fcntl_module.LOCK_NB)  # ty: ignore[unresolved-attribute]
    except BlockingIOError as error:
        logger.error("Another instance is already running", extra={"lock_path": str(lock_path)})
        raise SingleInstanceError(f"Another instance is already running (lock file: {lock_path})") from error


def _write_pid_to_lock(lock_file: object) -> None:
    lock_file.seek(0)  # ty: ignore[unresolved-attribute]
    lock_file.truncate()  # ty: ignore[unresolved-attribute]
    lock_file.write(str(os.getpid()))  # ty: ignore[unresolved-attribute]
    lock_file.flush()  # ty: ignore[unresolved-attribute]


def _resolve_posix_lock_path(name: str) -> Path:
    lock_filename = f"{_APP_NAME}.{name}.pid"
    runtime_directory = os.environ.get("XDG_RUNTIME_DIR")
    if runtime_directory:
        return Path(runtime_directory) / lock_filename
    return get_user_data_dir() / lock_filename


_WINDOWS_ERROR_ALREADY_EXISTS = 183


@contextlib.contextmanager
def _acquire_windows_mutex(name: str) -> Iterator[None]:
    import ctypes

    kernel32 = _bind_windows_mutex_api()
    mutex_name = f"{_APP_NAME}-{name}"
    mutex_handle = kernel32.CreateMutexW(None, True, mutex_name)
    last_error = ctypes.GetLastError()  # ty: ignore[unresolved-attribute]
    if not mutex_handle or last_error == _WINDOWS_ERROR_ALREADY_EXISTS:
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


def _bind_windows_mutex_api():  # noqa: ANN201 — opaque ctypes WinDLL handle; no useful annotation
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.windll.kernel32  # ty: ignore[unresolved-attribute]
    kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
    kernel32.CreateMutexW.restype = wintypes.HANDLE
    kernel32.ReleaseMutex.argtypes = [wintypes.HANDLE]
    kernel32.ReleaseMutex.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    return kernel32
