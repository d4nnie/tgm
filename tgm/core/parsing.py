import json
from dataclasses import dataclass
from datetime import datetime

from tgm.core.types import ChatDialog, ChatType, Message


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
        return "supergroup" if getattr(entity, "megagroup", False) else "channel"
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
    reply_to_message_id = getattr(telethon_message, "reply_to_msg_id", None)
    sender_id = _extract_sender_id(sender)
    edit_date = getattr(telethon_message, "edit_date", None)
    return Message(
        chat_id=chat_id,
        message_id=int(getattr(telethon_message, "id", 0)),
        timestamp=timestamp,
        sender_id=sender_id,
        sender_name=extract_sender_name(sender),
        text=text,
        reply_to_message_id=int(reply_to_message_id) if reply_to_message_id else None,
        edited_at=edit_date,
        raw_json=raw_json,
    )


def _extract_sender_id(sender: object) -> int | None:
    if sender is None:
        return None
    return int(getattr(sender, "id", 0))


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


def build_chat_dialog_from_telethon(dialog: object) -> ChatDialog:
    entity = getattr(dialog, "entity", None)
    return ChatDialog(
        chat_id=int(getattr(dialog, "id", 0)),
        title=extract_entity_display_name(entity),
        chat_type=classify_telethon_entity(entity),
    )
