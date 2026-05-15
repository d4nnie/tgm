from collections.abc import Callable
from dataclasses import dataclass

StatusCallback = Callable[[str], None]

_FLOOD_WAIT_ERROR_NAME = "FloodWaitError"
_FLOOD_WAIT_CAP_SECONDS = 600
_SESSION_EXPIRED_ERROR_NAMES: frozenset[str] = frozenset(
    {
        "AuthKeyError",
        "AuthKeyUnregisteredError",
        "AuthKeyDuplicatedError",
        "UserDeactivatedError",
        "UserDeactivatedBanError",
    }
)
_TELETHON_SERVER_ERROR_NAMES: frozenset[str] = frozenset({"ServerError", "RpcCallFailError", "RpcMcgetFailError"})
_NETWORK_ERROR_TYPES: tuple[type[BaseException], ...] = (
    ConnectionError,
    OSError,
    TimeoutError,
)
_MAX_NETWORK_RETRIES = 6
_NETWORK_BACKOFF_CAP_SECONDS = 30


class SessionExpiredError(RuntimeError):
    pass


class NetworkError(RuntimeError):
    pass


class FloodWaitTooLongError(RuntimeError):
    pass


class SingleInstanceError(RuntimeError):
    pass


@dataclass(frozen=True)
class FloodWaitOutcome:
    wait_seconds: int


@dataclass(frozen=True)
class FloodWaitTooLongOutcome:
    wait_seconds: int


@dataclass(frozen=True)
class SessionExpiredOutcome:
    pass


@dataclass(frozen=True)
class NetworkRetryOutcome:
    wait_seconds: int
    attempt: int


ErrorOutcome = FloodWaitOutcome | FloodWaitTooLongOutcome | SessionExpiredOutcome | NetworkRetryOutcome


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
class RaiseFloodWaitTooLongAction:
    wait_seconds: int


@dataclass(frozen=True)
class ReraiseAction:
    pass


RetryAction = (
    RetrySleepAction | RaiseSessionExpiredAction | RaiseNetworkAction | RaiseFloodWaitTooLongAction | ReraiseAction
)


def classify_telethon_error(error: BaseException, attempt: int) -> ErrorOutcome | None:
    name = type(error).__name__

    if name == _FLOOD_WAIT_ERROR_NAME:
        wait_seconds = int(getattr(error, "seconds", 0))
        if wait_seconds > _FLOOD_WAIT_CAP_SECONDS:
            return FloodWaitTooLongOutcome(wait_seconds=wait_seconds)
        return FloodWaitOutcome(wait_seconds=wait_seconds)

    if name in _SESSION_EXPIRED_ERROR_NAMES:
        return SessionExpiredOutcome()

    if name in _TELETHON_SERVER_ERROR_NAMES:
        return _maybe_network_retry(attempt)

    if isinstance(error, _NETWORK_ERROR_TYPES):
        return _maybe_network_retry(attempt)

    return None


def _maybe_network_retry(attempt: int) -> NetworkRetryOutcome | None:
    if attempt >= _MAX_NETWORK_RETRIES:
        return None
    wait_seconds = min(2**attempt, _NETWORK_BACKOFF_CAP_SECONDS)
    return NetworkRetryOutcome(wait_seconds=wait_seconds, attempt=attempt)


def decide_retry_action(error: BaseException, attempt: int) -> RetryAction:
    outcome = classify_telethon_error(error, attempt)

    match outcome:
        case FloodWaitOutcome(wait_seconds):
            return RetrySleepAction(
                seconds=wait_seconds,
                message=f"Throttled by Telegram, retry in {wait_seconds}s",
            )
        case FloodWaitTooLongOutcome(wait_seconds):
            return RaiseFloodWaitTooLongAction(wait_seconds=wait_seconds)
        case NetworkRetryOutcome(wait_seconds, attempt_value):
            return RetrySleepAction(
                seconds=wait_seconds,
                message=f"Network error, retry in {wait_seconds}s (attempt {attempt_value + 1}/{_MAX_NETWORK_RETRIES})",
            )
        case SessionExpiredOutcome():
            return RaiseSessionExpiredAction()
        case None:
            name = type(error).__name__
            if name in _TELETHON_SERVER_ERROR_NAMES or isinstance(error, _NETWORK_ERROR_TYPES):
                return RaiseNetworkAction()
            return ReraiseAction()
