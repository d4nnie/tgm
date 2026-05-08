import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

from tgm.core.errors import (
    NetworkError,
    RaiseNetworkAction,
    RaiseSessionExpiredAction,
    ReraiseAction,
    RetrySleepAction,
    SessionExpiredError,
    StatusCallback,
    decide_retry_action,
)

T = TypeVar("T")


async def with_telethon_guard(call_factory: Callable[[], Awaitable[T]], status_callback: StatusCallback) -> T:
    attempt = 0
    while True:
        try:
            return await call_factory()
        except Exception as error:
            action = decide_retry_action(error, attempt)

            match action:
                case RetrySleepAction(seconds, message):
                    status_callback(message)
                    await asyncio.sleep(seconds)
                    attempt += 1
                case RaiseSessionExpiredAction():
                    raise SessionExpiredError("Telegram session is no longer valid; re-run auth login") from error
                case RaiseNetworkAction():
                    raise NetworkError(f"network error after {attempt} retries: {error}") from error
                case ReraiseAction():
                    raise
