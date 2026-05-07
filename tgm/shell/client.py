from collections.abc import Awaitable, Callable
from dataclasses import dataclass, replace
from pathlib import Path

from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

from tgm.core.types import TelegramCreds
from tgm.shell.config import load_telegram_creds, save_telegram_creds, save_telegram_phone
from tgm.shell.platform import restrict_path_access, user_data_dir

_SESSION_BASENAME = "session"


@dataclass(frozen=True)
class LoginCallbacks:
    request_api_id: Callable[[], Awaitable[int]]
    request_api_hash: Callable[[], Awaitable[str]]
    request_phone: Callable[[], Awaitable[str]]
    request_sms_code: Callable[[], Awaitable[str]]
    request_password: Callable[[], Awaitable[str]]


async def login(callbacks: LoginCallbacks) -> TelegramClient:
    creds, fresh_api_creds, fresh_phone = await _resolve_creds(callbacks)

    client = TelegramClient(_telethon_session_argument(), creds.api_id, creds.api_hash)
    await client.connect()

    if not await client.is_user_authorized():
        await _interactive_sign_in(client, creds, callbacks)
        restrict_path_access(_session_file())

    if fresh_api_creds:
        save_telegram_creds(creds)
    elif fresh_phone and creds.phone is not None:
        save_telegram_phone(creds.phone)

    return client


async def _resolve_creds(callbacks: LoginCallbacks) -> tuple[TelegramCreds, bool, bool]:
    loaded = load_telegram_creds()

    if loaded is None:
        api_id = await callbacks.request_api_id()
        api_hash = await callbacks.request_api_hash()
        phone = await callbacks.request_phone()
        return TelegramCreds(api_id=api_id, api_hash=api_hash, phone=phone), True, True

    if loaded.phone is None:
        phone = await callbacks.request_phone()
        return replace(loaded, phone=phone), False, True

    return loaded, False, False


async def _interactive_sign_in(
    client: TelegramClient,
    creds: TelegramCreds,
    callbacks: LoginCallbacks,
) -> None:
    assert creds.phone is not None
    await client.send_code_request(creds.phone)
    sms_code = await callbacks.request_sms_code()
    try:
        await client.sign_in(creds.phone, sms_code)
    except SessionPasswordNeededError:
        password = await callbacks.request_password()
        await client.sign_in(password=password)


def _telethon_session_argument() -> str:
    return str(user_data_dir() / _SESSION_BASENAME)


def _session_file() -> Path:
    return user_data_dir() / f"{_SESSION_BASENAME}.session"
