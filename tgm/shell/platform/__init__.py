import contextlib
import getpass
import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import platformdirs

_APP_NAME = "telegram-monitor"
_CONFIG_FILENAME = "config.toml"
_LOCK_FILENAME = "telegram-monitor.pid"
_WINDOWS_MUTEX_NAME = "telegram-monitor-single-instance"


class SingleInstanceError(RuntimeError):
    pass


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
def acquire_single_instance_lock() -> Iterator[None]:
    if sys.platform == "win32":
        with _acquire_windows_mutex():
            yield
    else:
        with _acquire_posix_flock():
            yield


def _restrict_path_access_windows(path: Path) -> None:
    username = getpass.getuser()
    ace = f"{username}:(OI)(CI)F" if path.is_dir() else f"{username}:F"
    subprocess.run(
        ["icacls", str(path), "/inheritance:r", "/grant:r", ace],
        check=True,
        capture_output=True,
    )


@contextlib.contextmanager
def _acquire_posix_flock() -> Iterator[None]:
    import fcntl

    lock_path = _resolve_posix_lock_path()
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.touch(exist_ok=True)

    with open(lock_path, "r+") as lock_file:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise SingleInstanceError(f"Another instance is already running (lock file: {lock_path})") from error

        lock_file.seek(0)
        lock_file.truncate()
        lock_file.write(str(os.getpid()))
        lock_file.flush()

        yield


def _resolve_posix_lock_path() -> Path:
    runtime_directory = os.environ.get("XDG_RUNTIME_DIR")
    if runtime_directory:
        return Path(runtime_directory) / _LOCK_FILENAME
    return get_user_data_dir() / _LOCK_FILENAME


@contextlib.contextmanager
def _acquire_windows_mutex() -> Iterator[None]:
    import ctypes
    from ctypes import wintypes

    error_already_exists = 183

    kernel32 = ctypes.windll.kernel32  # ty: ignore[unresolved-attribute]
    kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
    kernel32.CreateMutexW.restype = wintypes.HANDLE
    kernel32.ReleaseMutex.argtypes = [wintypes.HANDLE]
    kernel32.ReleaseMutex.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL

    mutex_handle = kernel32.CreateMutexW(None, True, _WINDOWS_MUTEX_NAME)
    last_error = ctypes.GetLastError()  # ty: ignore[unresolved-attribute]

    if not mutex_handle or last_error == error_already_exists:
        if mutex_handle:
            kernel32.CloseHandle(mutex_handle)
        raise SingleInstanceError(f"Another instance is already running (Windows mutex: {_WINDOWS_MUTEX_NAME})")

    try:
        yield
    finally:
        kernel32.ReleaseMutex(mutex_handle)
        kernel32.CloseHandle(mutex_handle)
