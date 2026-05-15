import json
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from tgm.core.parsing import (
    convert_row_to_chat,
    convert_row_to_chat_profile,
    convert_row_to_feedback,
    convert_row_to_importance_criteria,
    convert_row_to_message,
    convert_row_to_run_state,
)
from tgm.core.types import Chat, ChatProfile, Feedback, ImportanceCriteria, Message, RunState
from tgm.shell.orm import (
    ChatProfileRow,
    ChatRow,
    FeedbackRow,
    ImportanceCriterionRow,
    MessageRow,
    RunStateRow,
    UserProfileRow,
)

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
) -> int:
    result = session.execute(
        update(MessageRow)
        .where(MessageRow.chat_id == chat_id, MessageRow.message_id == message_id)
        .values(text=text, edited_at=edited_at, raw_json=raw_json)
    )
    return int(result.rowcount or 0)  # ty: ignore[unresolved-attribute]


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


def get_chat_profile(session: Session, chat_id: int) -> ChatProfile | None:
    row = session.execute(select(ChatProfileRow).where(ChatProfileRow.chat_id == chat_id)).scalar_one_or_none()
    if row is None:
        return None
    return convert_row_to_chat_profile(row)


def upsert_chat_profile_description(session: Session, *, chat_id: int, description_prompt: str, now: datetime) -> None:
    statement = (
        sqlite_insert(ChatProfileRow)
        .values(chat_id=chat_id, description_prompt=description_prompt, updated_at=now)
        .on_conflict_do_update(
            index_elements=["chat_id"],
            set_={"description_prompt": description_prompt, "updated_at": now},
        )
    )
    session.execute(statement)


def update_chat_period(session: Session, *, chat_id: int, period_n_minutes: int) -> None:
    session.execute(update(ChatRow).where(ChatRow.chat_id == chat_id).values(period_n_minutes=period_n_minutes))


def get_active_criteria(session: Session, scope: str) -> ImportanceCriteria | None:
    row = session.execute(
        select(ImportanceCriterionRow)
        .where(ImportanceCriterionRow.scope == scope)
        .order_by(ImportanceCriterionRow.version.desc())
        .limit(1)
    ).scalar_one_or_none()
    if row is None:
        return None
    return convert_row_to_importance_criteria(row)


def insert_feedback(
    session: Session,
    *,
    chat_id: int,
    message_ids: list[int],
    user_comment: str | None,
    scope: str,
    marked_at: datetime,
) -> int:
    row = FeedbackRow(
        chat_id=chat_id,
        message_ids_json=json.dumps(message_ids),
        user_comment=user_comment,
        scope=scope,
        consumed=False,
        marked_at=marked_at,
    )
    session.add(row)
    session.flush()
    return int(row.id)


def get_unconsumed_feedback(session: Session, *, scope: str, chat_id: int | None = None) -> list[Feedback]:
    query = select(FeedbackRow).where(FeedbackRow.scope == scope, ~FeedbackRow.consumed)
    if chat_id is not None:
        query = query.where(FeedbackRow.chat_id == chat_id)
    rows = session.execute(query.order_by(FeedbackRow.marked_at)).scalars().all()
    return [convert_row_to_feedback(row) for row in rows]


def mark_feedback_consumed(session: Session, feedback_ids: list[int]) -> None:
    if not feedback_ids:
        return
    session.execute(update(FeedbackRow).where(FeedbackRow.id.in_(feedback_ids)).values(consumed=True))


def get_messages_by_ids(session: Session, *, chat_id: int, message_ids: list[int]) -> list[Message]:
    if not message_ids:
        return []
    rows = (
        session.execute(
            select(MessageRow)
            .where(MessageRow.chat_id == chat_id, MessageRow.message_id.in_(message_ids))
            .order_by(MessageRow.timestamp)
        )
        .scalars()
        .all()
    )
    return [convert_row_to_message(row) for row in rows]


def get_criteria_by_version(session: Session, *, scope: str, version: int) -> ImportanceCriteria | None:
    row = session.execute(
        select(ImportanceCriterionRow).where(
            ImportanceCriterionRow.scope == scope, ImportanceCriterionRow.version == version
        )
    ).scalar_one_or_none()
    if row is None:
        return None
    return convert_row_to_importance_criteria(row)


def insert_criteria(session: Session, *, scope: str, criteria_text: str, now: datetime) -> int:
    max_version = session.execute(
        select(ImportanceCriterionRow.version)
        .where(ImportanceCriterionRow.scope == scope)
        .order_by(ImportanceCriterionRow.version.desc())
        .limit(1)
    ).scalar_one_or_none()
    new_version = (int(max_version) if max_version is not None else 0) + 1
    session.add(
        ImportanceCriterionRow(
            scope=scope,
            criteria_text=criteria_text,
            version=new_version,
            updated_at=now,
        )
    )
    session.flush()
    return new_version
