from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from tgm.core.parsing import convert_row_to_chat, convert_row_to_run_state
from tgm.core.types import Chat, Message, RunState
from tgm.shell.orm import ChatRow, MessageRow, RunStateRow, UserProfileRow

_ABOUT_ME_KEY = "about_me"


def insert_message(session: Session, message: Message) -> None:
    statement = (
        sqlite_insert(MessageRow)
        .values(
            chat_id=message.chat_id,
            msg_id=message.message_id,
            ts=message.timestamp,
            sender_id=message.sender_id,
            sender_name=message.sender_name,
            text=message.text,
            reply_to_msg_id=message.reply_to_message_id,
            edited_at=message.edited_at,
            raw_json=message.raw_json,
        )
        .on_conflict_do_nothing()
    )
    session.execute(statement)


def update_message_edit(
    session: Session,
    *,
    chat_id: int,
    message_id: int,
    text: str | None,
    edited_at: datetime,
    raw_json: str,
) -> None:
    session.execute(
        update(MessageRow)
        .where(MessageRow.chat_id == chat_id, MessageRow.message_id == message_id)
        .values(text=text, edited_at=edited_at, raw_json=raw_json)
    )


def upsert_chat(session: Session, chat: Chat) -> None:
    statement = (
        sqlite_insert(ChatRow)
        .values(
            chat_id=chat.chat_id,
            title=chat.title,
            type=chat.chat_type,
            is_monitored=chat.is_monitored,
            period_n_minutes=chat.period_n_minutes,
            added_at=chat.added_at,
        )
        .on_conflict_do_update(
            index_elements=["chat_id"],
            set_={
                "title": chat.title,
                "type": chat.chat_type,
                "is_monitored": chat.is_monitored,
                "period_n_minutes": chat.period_n_minutes,
            },
        )
    )
    session.execute(statement)


def mark_chat_unmonitored(session: Session, chat_id: int) -> None:
    session.execute(update(ChatRow).where(ChatRow.chat_id == chat_id).values(is_monitored=False))


def is_chat_monitored(session: Session, chat_id: int) -> bool:
    flag = session.execute(select(ChatRow.is_monitored).where(ChatRow.chat_id == chat_id)).scalar_one_or_none()
    return bool(flag) if flag is not None else False


def list_monitored_chat_ids(session: Session) -> list[int]:
    rows = session.execute(select(ChatRow.chat_id).where(ChatRow.is_monitored)).scalars().all()
    return list(rows)


def list_chats(session: Session) -> list[Chat]:
    rows = session.execute(select(ChatRow).order_by(ChatRow.title)).scalars().all()
    return [convert_row_to_chat(row) for row in rows]


def get_run_state(session: Session, scope: str) -> RunState | None:
    row = session.execute(select(RunStateRow).where(RunStateRow.scope == scope)).scalar_one_or_none()
    if row is None:
        return None
    return convert_row_to_run_state(row)


def upsert_run_state(session: Session, state: RunState) -> None:
    statement = (
        sqlite_insert(RunStateRow)
        .values(scope=state.scope, last_run_at=state.last_run_at, last_msg_id=state.last_message_id)
        .on_conflict_do_update(
            index_elements=["scope"],
            set_={"last_run_at": state.last_run_at, "last_msg_id": state.last_message_id},
        )
    )
    session.execute(statement)


def get_user_profile_about_me(session: Session) -> str | None:
    return session.execute(select(UserProfileRow.value).where(UserProfileRow.key == _ABOUT_ME_KEY)).scalar_one_or_none()


def upsert_user_profile_about_me(session: Session, text: str) -> None:
    statement = (
        sqlite_insert(UserProfileRow)
        .values(key=_ABOUT_ME_KEY, value=text)
        .on_conflict_do_update(index_elements=["key"], set_={"value": text})
    )
    session.execute(statement)
