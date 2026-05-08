from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError

from tgm.core.auth import (
    Action,
    ApiCredentialsProvided,
    AuthorizationChecked,
    AuthorizationFlowError,
    CheckAuthorization,
    CodeRequested,
    CredentialsLoaded,
    CredentialsPersisted,
    Event,
    Finish,
    LoadCredentials,
    PasswordProvided,
    PasswordSignInCompleted,
    PersistFullCredentials,
    PersistPhone,
    PhoneProvided,
    RequestApiCredentials,
    RequestCode,
    RequestPassword,
    RequestPhone,
    RequestSmsCode,
    RestrictSession,
    SessionRestricted,
    SignInCompleted,
    SignInWithCode,
    SignInWithPassword,
    SmsCodeProvided,
    apply_event,
    create_initial_state,
    decide_next_action,
)
from tgm.core.parsing import (
    build_chat_dialog_from_telethon,
    build_edit_payload_from_telethon,
    build_message_from_telethon,
    get_chat_scope,
    serialize_telethon_message,
)
from tgm.core.types import ChatDialog, TelegramCredentials
from tgm.shell.config import (
    load_telegram_credentials,
    save_telegram_credentials,
    save_telegram_phone,
)
from tgm.shell.platform import get_user_data_dir, restrict_path_access
from tgm.shell.repos import (
    get_run_state,
    insert_message,
    is_chat_monitored,
    list_monitored_chat_ids,
    update_message_edit,
)

_SESSION_BASENAME = "session"

_CALLBACK_ACTION_TYPES: tuple[type, ...] = (
    RequestApiCredentials,
    RequestPhone,
    RequestSmsCode,
    RequestPassword,
)
_TELETHON_ACTION_TYPES: tuple[type, ...] = (
    CheckAuthorization,
    RequestCode,
    SignInWithCode,
    SignInWithPassword,
)


@dataclass(frozen=True)
class LoginCallbacks:
    request_api_id: Callable[[], Awaitable[int]]
    request_api_hash: Callable[[], Awaitable[str]]
    request_phone: Callable[[], Awaitable[str]]
    request_sms_code: Callable[[], Awaitable[str]]
    request_password: Callable[[], Awaitable[str]]


async def login(callbacks: LoginCallbacks) -> TelegramClient:
    state = create_initial_state()
    client: TelegramClient | None = None

    while True:
        action = decide_next_action(state)

        if isinstance(action, Finish):
            if client is None:
                raise AuthorizationFlowError("login completed without a connected Telethon client")
            return client

        client, event = await _execute_action(action, callbacks, client)
        state = apply_event(state, event)


async def _execute_action(
    action: Action,
    callbacks: LoginCallbacks,
    client: TelegramClient | None,
) -> tuple[TelegramClient | None, Event]:
    if isinstance(action, _CALLBACK_ACTION_TYPES):
        return client, await _execute_callback_action(action, callbacks)
    if isinstance(action, _TELETHON_ACTION_TYPES):
        return await _execute_telethon_action(action, client)
    return client, _execute_local_action(action)


async def _execute_callback_action(action: Action, callbacks: LoginCallbacks) -> Event:
    match action:
        case RequestApiCredentials():
            api_id = await callbacks.request_api_id()
            api_hash = await callbacks.request_api_hash()
            return ApiCredentialsProvided(api_id=api_id, api_hash=api_hash)
        case RequestPhone():
            return PhoneProvided(phone=await callbacks.request_phone())
        case RequestSmsCode():
            return SmsCodeProvided(code=await callbacks.request_sms_code())
        case RequestPassword():
            return PasswordProvided(password=await callbacks.request_password())
    raise AuthorizationFlowError(f"unexpected callback action: {action!r}")


async def _execute_telethon_action(action: Action, client: TelegramClient | None) -> tuple[TelegramClient, Event]:
    if isinstance(action, CheckAuthorization):
        return await _open_client_and_check_authorization(action.credentials)

    if client is None:
        raise AuthorizationFlowError(f"telethon action {type(action).__name__} requires a connected client")
    return await _execute_authenticated_action(action, client)


async def _open_client_and_check_authorization(
    credentials: TelegramCredentials,
) -> tuple[TelegramClient, Event]:
    client = TelegramClient(_evaluate_telethon_session_argument(), credentials.api_id, credentials.api_hash)
    await client.connect()
    authorized = await client.is_user_authorized()
    return client, AuthorizationChecked(authorized=authorized)


async def _execute_authenticated_action(action: Action, client: TelegramClient) -> tuple[TelegramClient, Event]:
    match action:
        case RequestCode(phone):
            await client.send_code_request(phone)
            return client, CodeRequested()
        case SignInWithCode(phone, code):
            password_required = await _try_sign_in_with_code(client, phone, code)
            return client, SignInCompleted(password_required=password_required)
        case SignInWithPassword(password):
            await client.sign_in(password=password)
            return client, PasswordSignInCompleted()
    raise AuthorizationFlowError(f"unexpected authenticated action: {action!r}")


async def _try_sign_in_with_code(client: TelegramClient, phone: str, code: str) -> bool:
    try:
        await client.sign_in(phone, code)
        return False
    except SessionPasswordNeededError:
        return True


def _execute_local_action(action: Action) -> Event:
    match action:
        case LoadCredentials():
            return CredentialsLoaded(load_telegram_credentials())
        case RestrictSession():
            restrict_path_access(_evaluate_session_file())
            return SessionRestricted()
        case PersistFullCredentials(credentials):
            save_telegram_credentials(credentials)
            return CredentialsPersisted()
        case PersistPhone(phone):
            save_telegram_phone(phone)
            return CredentialsPersisted()
    raise AuthorizationFlowError(f"unexpected local action: {action!r}")


def subscribe_to_message_events(client: TelegramClient, session: Session) -> None:
    @client.on(events.NewMessage())
    async def _on_new_message(event: events.NewMessage.Event) -> None:
        await _handle_new_message(session, event)

    @client.on(events.MessageEdited())
    async def _on_message_edited(event: events.MessageEdited.Event) -> None:
        await _handle_message_edited(session, event)


async def _handle_new_message(session: Session, event: events.NewMessage.Event) -> None:
    chat_id = event.chat_id
    if chat_id is None or not is_chat_monitored(session, int(chat_id)):
        return

    sender = await event.get_sender()
    message = build_message_from_telethon(
        chat_id=int(chat_id),
        telethon_message=event.message,
        sender=sender,
        raw_json=serialize_telethon_message(event.message),
        fallback_timestamp=datetime.now(UTC),
    )
    insert_message(session, message)
    session.commit()


async def _handle_message_edited(session: Session, event: events.MessageEdited.Event) -> None:
    chat_id = event.chat_id
    if chat_id is None or not is_chat_monitored(session, int(chat_id)):
        return

    payload = build_edit_payload_from_telethon(
        chat_id=int(chat_id),
        telethon_message=event.message,
        raw_json=serialize_telethon_message(event.message),
        fallback_edited_at=datetime.now(UTC),
    )
    update_message_edit(
        session,
        chat_id=payload.chat_id,
        msg_id=payload.msg_id,
        text=payload.text,
        edited_at=payload.edited_at,
        raw_json=payload.raw_json,
    )
    session.commit()


async def fetch_dialogs(client: TelegramClient) -> list[ChatDialog]:
    dialogs: list[ChatDialog] = []
    async for dialog in client.iter_dialogs():
        dialogs.append(build_chat_dialog_from_telethon(dialog))
    return dialogs


async def backfill_messages(client: TelegramClient, session: Session) -> None:
    for chat_id in list_monitored_chat_ids(session):
        await _backfill_chat(client, session, chat_id)


async def _backfill_chat(client: TelegramClient, session: Session, chat_id: int) -> None:
    state = get_run_state(session, get_chat_scope(chat_id))
    if state is None or state.last_msg_id is None:
        return

    async for telethon_message in client.iter_messages(chat_id, min_id=state.last_msg_id):
        sender = await telethon_message.get_sender()
        message = build_message_from_telethon(
            chat_id=chat_id,
            telethon_message=telethon_message,
            sender=sender,
            raw_json=serialize_telethon_message(telethon_message),
            fallback_timestamp=datetime.now(UTC),
        )
        insert_message(session, message)

    session.commit()


def _evaluate_telethon_session_argument() -> str:
    return str(get_user_data_dir() / _SESSION_BASENAME)


def _evaluate_session_file() -> Path:
    return get_user_data_dir() / f"{_SESSION_BASENAME}.session"
