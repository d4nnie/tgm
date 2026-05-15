import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import NoReturn, TypeVar

from tgm.core.errors import (
    FloodWaitTooLongError,
    NetworkError,
    RaiseFloodWaitTooLongAction,
    RaiseNetworkAction,
    RaiseSessionExpiredAction,
    ReraiseAction,
    RetryAction,
    RetrySleepAction,
    SessionExpiredError,
    decide_retry_action,
)
from tgm.core.types import StatusCallback

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def do_with_telethon_guard(call_factory: Callable[[], Awaitable[T]], status_callback: StatusCallback) -> T:
    attempt = 0
    last_reason: str | None = None
    while True:
        try:
            return await call_factory()
        except Exception as error:
            action = decide_retry_action(error, attempt)
            last_reason, attempt = await _apply_retry_action(action, error, attempt, last_reason, status_callback)


async def _apply_retry_action(  # noqa: PLR0915  # FSM mapper: one match arm per RetryAction variant.
    action: RetryAction,
    error: Exception,
    attempt: int,
    last_reason: str | None,
    status_callback: StatusCallback,
) -> tuple[str | None, int]:
    match action:
        case RetrySleepAction(seconds, message):
            return await _sleep_and_continue(seconds, message, attempt, last_reason, status_callback)
        case RaiseSessionExpiredAction():
            _raise_session_expired(error, attempt)
        case RaiseNetworkAction():
            _raise_network(error, attempt)
        case RaiseFloodWaitTooLongAction(wait_seconds):
            _raise_flood_wait_too_long(error, wait_seconds, status_callback)
        case ReraiseAction():
            logger.error("Unhandled Telegram error", extra={"error_type": type(error).__name__})
            raise


async def _sleep_and_continue(
    seconds: int,
    message: str,
    attempt: int,
    last_reason: str | None,
    status_callback: StatusCallback,
) -> tuple[str, int]:
    if message != last_reason:
        logger.warning(
            "Retrying after Telegram error",
            extra={"attempt": attempt, "sleep_seconds": seconds, "reason": message},
        )
    status_callback(message)
    await asyncio.sleep(seconds)
    return message, attempt + 1


def _raise_session_expired(error: Exception, attempt: int) -> NoReturn:
    logger.error("Telegram session expired", extra={"attempts": attempt})
    raise SessionExpiredError("Telegram session is no longer valid; re-run auth login") from error


def _raise_network(error: Exception, attempt: int) -> NoReturn:
    logger.error("Telegram network error gave up", extra={"attempts": attempt})
    raise NetworkError(f"network error after {attempt} retries: {error}") from error


def _raise_flood_wait_too_long(error: Exception, wait_seconds: int, status_callback: StatusCallback) -> NoReturn:
    minutes = max(1, wait_seconds // 60)
    friendly = f"Telegram попросил подождать {minutes} мин — аккаунт временно ограничен. Попробуйте позже."
    logger.error("Telegram FloodWait exceeded cap", extra={"wait_seconds": wait_seconds})
    status_callback(friendly)
    raise FloodWaitTooLongError(f"Telegram requested {wait_seconds}s wait — account temporarily restricted") from error
