import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

from tgm.core.errors import (
    FloodWaitTooLongError,
    NetworkError,
    RaiseFloodWaitTooLongAction,
    RaiseNetworkAction,
    RaiseSessionExpiredAction,
    ReraiseAction,
    RetrySleepAction,
    SessionExpiredError,
    StatusCallback,
    decide_retry_action,
)

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

            match action:
                case RetrySleepAction(seconds, message):
                    if message != last_reason:
                        logger.warning(
                            "Retrying after Telegram error",
                            extra={"attempt": attempt, "sleep_seconds": seconds, "reason": message},
                        )
                        last_reason = message
                    status_callback(message)
                    await asyncio.sleep(seconds)
                    attempt += 1
                case RaiseSessionExpiredAction():
                    logger.error("Telegram session expired", extra={"attempts": attempt})
                    raise SessionExpiredError("Telegram session is no longer valid; re-run auth login") from error
                case RaiseNetworkAction():
                    logger.error("Telegram network error gave up", extra={"attempts": attempt})
                    raise NetworkError(f"network error after {attempt} retries: {error}") from error
                case RaiseFloodWaitTooLongAction(wait_seconds):
                    minutes = max(1, wait_seconds // 60)
                    friendly = (
                        f"Telegram попросил подождать {minutes} мин — аккаунт временно ограничен. Попробуйте позже."
                    )
                    logger.error("Telegram FloodWait exceeded cap", extra={"wait_seconds": wait_seconds})
                    status_callback(friendly)
                    raise FloodWaitTooLongError(
                        f"Telegram requested {wait_seconds}s wait — account temporarily restricted"
                    ) from error
                case ReraiseAction():
                    logger.error("Unhandled Telegram error", extra={"error_type": type(error).__name__})
                    raise
