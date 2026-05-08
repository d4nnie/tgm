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


@dataclass(frozen=True)
class RetrySleepAction:
    seconds: int
    message: str


@dataclass(frozen=True)
class RaiseSessionExpiredAction:
    pass


@dataclass(frozen=True)
class RaiseNetworkAction:
    pass


@dataclass(frozen=True)
class ReraiseAction:
    pass


RetryAction = RetrySleepAction | RaiseSessionExpiredAction | RaiseNetworkAction | ReraiseAction


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


def decide_retry_action(error: BaseException, attempt: int) -> RetryAction:
    outcome = classify_telethon_error(error, attempt)

    match outcome:
        case FloodWaitOutcome(wait_seconds):
            return RetrySleepAction(
                seconds=wait_seconds,
                message=f"Throttled by Telegram, retry in {wait_seconds}s",
            )
        case NetworkRetryOutcome(wait_seconds, attempt_value):
            return RetrySleepAction(
                seconds=wait_seconds,
                message=f"Network error, retry in {wait_seconds}s (attempt {attempt_value + 1}/{_MAX_NETWORK_RETRIES})",
            )
        case SessionExpiredOutcome():
            return RaiseSessionExpiredAction()
        case None:
            if isinstance(error, _NETWORK_ERROR_TYPES):
                return RaiseNetworkAction()
            return ReraiseAction()
