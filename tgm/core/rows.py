import json
from datetime import datetime
from typing import Literal, Protocol, cast

from tgm.core.types import (
    Chat,
    ChatProfile,
    ChatType,
    Feedback,
    ImportanceCriteria,
    Message,
    RunState,
)


class ChatRowLike(Protocol):
    chat_id: int
    title: str
    chat_type: str
    is_monitored: bool
    period_n_minutes: int
    added_at: datetime


class MessageRowLike(Protocol):
    chat_id: int
    message_id: int
    timestamp: datetime
    sender_id: int | None
    sender_name: str | None
    text: str | None
    reply_to_message_id: int | None
    edited_at: datetime | None
    raw_json: str


class RunStateRowLike(Protocol):
    scope: str
    last_run_at: datetime | None
    last_message_id: int | None


class FeedbackRowLike(Protocol):
    id: int
    chat_id: int
    message_ids_json: str
    user_comment: str | None
    scope: str
    consumed: bool
    marked_at: datetime


class ImportanceCriterionRowLike(Protocol):
    id: int
    scope: str
    criteria_text: str
    version: int
    updated_at: datetime


class ChatProfileRowLike(Protocol):
    chat_id: int
    description_prompt: str
    rolling_summary: str
    updated_at: datetime


def convert_row_to_chat(row: ChatRowLike) -> Chat:
    return Chat(
        chat_id=int(row.chat_id),
        title=str(row.title),
        chat_type=cast(ChatType, row.chat_type),
        is_monitored=bool(row.is_monitored),
        period_n_minutes=int(row.period_n_minutes),
        added_at=row.added_at,
    )


def convert_row_to_message(row: MessageRowLike) -> Message:
    return Message(
        chat_id=int(row.chat_id),
        message_id=int(row.message_id),
        timestamp=row.timestamp,
        sender_id=row.sender_id,
        sender_name=row.sender_name,
        text=row.text,
        reply_to_message_id=row.reply_to_message_id,
        edited_at=row.edited_at,
        raw_json=str(row.raw_json),
    )


def convert_row_to_run_state(row: RunStateRowLike) -> RunState:
    last_message_id = int(row.last_message_id) if row.last_message_id is not None else None
    return RunState(
        scope=str(row.scope),
        last_run_at=row.last_run_at,
        last_message_id=last_message_id,
    )


def convert_row_to_feedback(row: FeedbackRowLike) -> Feedback:
    raw_json = row.message_ids_json or "[]"
    raw_message_ids = json.loads(raw_json)

    return Feedback(
        id=int(row.id),
        chat_id=int(row.chat_id),
        message_ids=tuple(int(value) for value in raw_message_ids),
        user_comment=row.user_comment,
        scope=cast(Literal["chat", "global"], row.scope),
        consumed=bool(row.consumed),
        marked_at=row.marked_at,
    )


def convert_row_to_importance_criteria(row: ImportanceCriterionRowLike) -> ImportanceCriteria:
    return ImportanceCriteria(
        id=int(row.id),
        scope=str(row.scope),
        criteria_text=str(row.criteria_text),
        version=int(row.version),
        updated_at=row.updated_at,
    )


def convert_row_to_chat_profile(row: ChatProfileRowLike) -> ChatProfile:
    return ChatProfile(
        chat_id=int(row.chat_id),
        description_prompt=str(row.description_prompt or ""),
        rolling_summary=str(row.rolling_summary or ""),
        updated_at=row.updated_at,
    )
