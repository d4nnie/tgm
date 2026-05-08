from collections.abc import Callable
from dataclasses import dataclass

StatusCallback = Callable[[str], None]

_FLOOD_WAIT_ERROR_NAME = "FloodWaitError"
_SESSION_EXPIRED_ERROR_NAMES: frozenset[str] = frozenset(
    {"AuthKeyError", "AuthKeyUnregisteredError", "UserDeactivatedError"}
)
_NETWORK_ERROR_TYPES: tuple[type[BaseException], ...] = (
    ConnectionError,
    OSError,
    TimeoutError,
)
_MAX_NETWORK_RETRIES = 5
_NETWORK_BACKOFF_CAP_SECONDS = 30


class SessionExpiredError(RuntimeError):
    pass


class NetworkError(RuntimeError):
    pass


@dataclass(frozen=True)
class FloodWaitOutcome:
    wait_seconds: int


@dataclass(frozen=True)
class SessionExpiredOutcome:
    pass


@dataclass(frozen=True)
class NetworkRetryOutcome:
    wait_seconds: int
    attempt: int


ErrorOutcome = FloodWaitOutcome | SessionExpiredOutcome | NetworkRetryOutcome


def classify_telethon_error(error: BaseException, attempt: int) -> ErrorOutcome | None:
    name = type(error).__name__

    if name == _FLOOD_WAIT_ERROR_NAME:
        return FloodWaitOutcome(wait_seconds=int(getattr(error, "seconds", 0)))

    if name in _SESSION_EXPIRED_ERROR_NAMES:
        return SessionExpiredOutcome()

    if isinstance(error, _NETWORK_ERROR_TYPES):
        if attempt >= _MAX_NETWORK_RETRIES:
            return None
        wait_seconds = min(2**attempt, _NETWORK_BACKOFF_CAP_SECONDS)
        return NetworkRetryOutcome(wait_seconds=wait_seconds, attempt=attempt)

    return None
