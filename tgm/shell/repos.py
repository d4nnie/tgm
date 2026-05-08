from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from tgm.core.parsing import row_to_chat
from tgm.core.types import Chat, Message
from tgm.shell.orm import ChatRow, MessageRow


def insert_message(session: Session, message: Message) -> None:
    statement = (
        sqlite_insert(MessageRow)
        .values(
            chat_id=message.chat_id,
            msg_id=message.msg_id,
            ts=message.timestamp,
            sender_id=message.sender_id,
            sender_name=message.sender_name,
            text=message.text,
            reply_to_msg_id=message.reply_to_msg_id,
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
    msg_id: int,
    text: str | None,
    edited_at: datetime,
    raw_json: str,
) -> None:
    session.execute(
        update(MessageRow)
        .where(MessageRow.chat_id == chat_id, MessageRow.msg_id == msg_id)
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
    return [row_to_chat(row) for row in rows]
