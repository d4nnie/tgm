import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, TypeVar, cast

from pydantic import BaseModel, ValidationError

from tgm.core.llm import LLMResponseError
from tgm.core.schemas import (
    CriteriaRecalcResponse,
    GlobalResponse,
    PerChatResponse,
)
from tgm.core.types import (
    Chat,
    ChatDialog,
    ChatProfile,
    ChatType,
    Feedback,
    ImportanceCriteria,
    Message,
    RunState,
)

_GLOBAL_SCOPE = "global"

_PydanticModel = TypeVar("_PydanticModel", bound=BaseModel)


def get_chat_scope(chat_id: int) -> str:
    return f"chat:{chat_id}"


def get_global_scope() -> str:
    return _GLOBAL_SCOPE


@dataclass(frozen=True)
class MessageEditPayload:
    chat_id: int
    message_id: int
    text: str | None
    edited_at: datetime
    raw_json: str


def extract_sender_name(sender: object) -> str | None:
    if sender is None:
        return None
    return _extract_title(sender) or _extract_full_name(sender) or _extract_username_handle(sender)


def _extract_title(sender: object) -> str | None:
    title = getattr(sender, "title", None)
    return str(title) if title else None


def _extract_full_name(sender: object) -> str | None:
    first = str(getattr(sender, "first_name", None) or "")
    last = str(getattr(sender, "last_name", None) or "")
    return f"{first} {last}".strip() or None


def _extract_username_handle(sender: object) -> str | None:
    username = getattr(sender, "username", None)
    return f"@{username}" if username else None


def extract_entity_display_name(entity: object) -> str:
    return extract_sender_name(entity) or f"id={getattr(entity, 'id', '?')}"


def classify_telethon_entity(entity: object) -> ChatType:
    if hasattr(entity, "first_name"):
        return "user"
    if hasattr(entity, "megagroup"):
        return "supergroup" if entity.megagroup else "channel"
    if hasattr(entity, "title"):
        return "group"
    raise ValueError(f"cannot classify entity: {type(entity).__name__}")


def build_message_from_telethon(
    *,
    chat_id: int,
    telethon_message: object,
    sender: object,
    raw_json: str,
    fallback_timestamp: datetime,
) -> Message:
    timestamp = getattr(telethon_message, "date", None) or fallback_timestamp
    text = getattr(telethon_message, "text", None) or None
    reply_to = getattr(telethon_message, "reply_to_msg_id", None)
    sender_id = int(getattr(sender, "id", 0)) if sender is not None else None

    return Message(
        chat_id=chat_id,
        message_id=int(getattr(telethon_message, "id", 0)),
        timestamp=timestamp,
        sender_id=sender_id,
        sender_name=extract_sender_name(sender),
        text=text,
        reply_to_message_id=int(reply_to) if reply_to else None,
        edited_at=None,
        raw_json=raw_json,
    )


def serialize_telethon_message(message: object) -> str:
    payload = message.to_dict()  # ty: ignore[unresolved-attribute]
    return json.dumps(payload, default=str, ensure_ascii=False)


def build_edit_payload_from_telethon(
    *,
    chat_id: int,
    telethon_message: object,
    raw_json: str,
    fallback_edited_at: datetime,
) -> MessageEditPayload:
    edited_at = getattr(telethon_message, "edit_date", None) or fallback_edited_at
    text = getattr(telethon_message, "text", None) or None

    return MessageEditPayload(
        chat_id=chat_id,
        message_id=int(getattr(telethon_message, "id", 0)),
        text=text,
        edited_at=edited_at,
        raw_json=raw_json,
    )


def convert_row_to_chat(row: Any) -> Chat:
    return Chat(
        chat_id=int(row.chat_id),
        title=str(row.title),
        chat_type=cast(ChatType, row.chat_type),
        is_monitored=bool(row.is_monitored),
        period_n_minutes=int(row.period_n_minutes),
        added_at=row.added_at,
    )


def convert_row_to_message(row: Any) -> Message:
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


def convert_row_to_run_state(row: Any) -> RunState:
    return RunState(
        scope=str(row.scope),
        last_run_at=row.last_run_at,
        last_message_id=int(row.last_message_id) if row.last_message_id is not None else None,
    )


def convert_row_to_feedback(row: Any) -> Feedback:
    raw_message_ids = json.loads(str(row.message_ids_json or "[]"))
    return Feedback(
        id=int(row.id),
        chat_id=int(row.chat_id),
        message_ids=[int(value) for value in raw_message_ids],
        user_comment=row.user_comment,
        scope=cast(Literal["chat", "global"], row.scope),
        consumed=bool(row.consumed),
        marked_at=row.marked_at,
    )


def convert_row_to_importance_criteria(row: Any) -> ImportanceCriteria:
    return ImportanceCriteria(
        id=int(row.id),
        scope=str(row.scope),
        criteria_text=str(row.criteria_text),
        version=int(row.version),
        updated_at=row.updated_at,
    )


def convert_row_to_chat_profile(row: Any) -> ChatProfile:
    return ChatProfile(
        chat_id=int(row.chat_id),
        description_prompt=str(row.description_prompt or ""),
        rolling_summary=str(row.rolling_summary or ""),
        updated_at=row.updated_at,
    )


def build_chat_dialog_from_telethon(dialog: Any) -> ChatDialog:
    return ChatDialog(
        chat_id=int(dialog.id),
        title=extract_entity_display_name(dialog.entity),
        chat_type=classify_telethon_entity(dialog.entity),
    )


def parse_per_chat_response(payload: Mapping[str, Any], *, known_message_ids: set[int]) -> PerChatResponse:
    response = _model_validate_or_wrap(PerChatResponse, payload)
    _require_non_empty(response.summary, "summary")
    _require_non_empty(response.updated_rolling_summary, "updated_rolling_summary")
    for highlight in response.highlights:
        _require_non_empty(highlight.why, "highlights[].why")
        if highlight.message_id not in known_message_ids:
            raise LLMResponseError(f"highlight references unknown message_id={highlight.message_id}")
    return response


def parse_global_response(
    payload: Mapping[str, Any], *, known_chat_message_pairs: set[tuple[int, int]]
) -> GlobalResponse:
    response = _model_validate_or_wrap(GlobalResponse, payload)
    _require_non_empty(response.summary, "summary")
    for highlight in response.highlights:
        _require_non_empty(highlight.why, "highlights[].why")
        pair = (highlight.chat_id, highlight.message_id)
        if pair not in known_chat_message_pairs:
            raise LLMResponseError(
                f"highlight references unknown (chat_id={highlight.chat_id}, message_id={highlight.message_id})"
            )
    return response


def parse_criteria_response(payload: Mapping[str, Any]) -> CriteriaRecalcResponse:
    response = _model_validate_or_wrap(CriteriaRecalcResponse, payload)
    _require_non_empty(response.new_criteria_text, "new_criteria_text")
    _require_non_empty(response.what_changed, "what_changed")
    return response


def _model_validate_or_wrap(model_class: type[_PydanticModel], payload: Mapping[str, Any]) -> _PydanticModel:
    try:
        return model_class.model_validate(dict(payload))
    except ValidationError as error:
        raise LLMResponseError(f"response does not match {model_class.__name__} schema: {error}") from error


def _require_non_empty(value: str, field_name: str) -> None:
    if not value or not value.strip():
        raise LLMResponseError(f"field {field_name!r} must be a non-empty string")
